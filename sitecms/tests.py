from django.conf import settings
from django.db import connection
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounts.backends import WagtailGroupPermissionsBackend
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.models import (
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Locale,
    Page,
    Site,
)

from .forms import CMSUserCreationForm, CMSUserEditForm
from .models import ContentPage, HomePage
from .viewsets import CMSUserFilterSet
from .permissions import (
    StaffCollectionManagementPermissionPolicy,
    StaffCollectionOwnershipPermissionPolicy,
    StaffPagePermissionPolicy,
)
from wagtail.permissions import policy_registry


class WagtailIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # config.test_settings disables migrations and syncs the live model
        # schema. Build the minimal Wagtail tree that the production data
        # migration creates so these tests exercise the same homepage lookup.
        if HomePage.objects.exists():
            return

        Locale.objects.get_or_create(language_code=settings.LANGUAGE_CODE)
        page_type = ContentType.objects.get_for_model(Page, for_concrete_model=False)
        home_type = ContentType.objects.get_for_model(HomePage, for_concrete_model=False)
        Page.objects.create(
            title="Root",
            slug="root",
            path="0001",
            depth=1,
            numchild=1,
            url_path="/",
            content_type=page_type,
        )
        base_home = Page.objects.create(
            title="صفحه اصلی نبیولا والت",
            slug="home",
            path="00010001",
            depth=2,
            numchild=0,
            url_path="/home/",
            content_type=home_type,
        )
        # Avoid a multi-table save rewriting the existing Page parent row.
        # This test uses config.test_settings (migrations disabled), so mirror
        # the production data migration's child-table insert.
        quote_name = connection.ops.quote_name
        child_table = quote_name(HomePage._meta.db_table)
        child_fields = [
            ("page_ptr", base_home.pk),
            ("hero_eyebrow", "متن بالای عنوان"),
            ("hero_title", "عنوان قابل ویرایش از Wagtail"),
            ("hero_highlight", "تأکید قابل ویرایش"),
            ("hero_description", "توضیحات قابل ویرایش"),
            ("hero_primary_cta_label", "کشف محصولات"),
            ("hero_primary_cta_url", "#products"),
            ("body", ""),
        ]
        columns = [
            quote_name(HomePage._meta.get_field(name).column)
            for name, _ in child_fields
        ]
        placeholders = ", ".join(["%s"] * len(child_fields))
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {child_table} ({', '.join(columns)}) "
                f"VALUES ({placeholders})",
                [value for _, value in child_fields],
            )
        homepage = HomePage.objects.get(pk=base_home.pk)
        Site.objects.create(
            hostname="testserver",
            port=80,
            is_default_site=True,
            root_page=homepage,
        )

    def test_existing_storefront_homepage_is_managed_by_wagtail(self):
        homepage = HomePage.objects.get(slug="home")
        self.assertEqual(
            Site.objects.get(is_default_site=True).root_page_id,
            homepage.pk,
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, homepage.hero_title)
        self.assertContains(response, homepage.hero_highlight)

    def test_published_wagtail_content_page_uses_canonical_root_url(self):
        homepage = HomePage.objects.get(slug="home")
        content_page = ContentPage(
            title="صفحه راهنمای آزمایشی",
            slug="cms-guide-test",
            intro="معرفی صفحه",
            body="<p>محتوای منتشرشده</p>",
        )
        homepage.add_child(instance=content_page)
        content_page.save_revision().publish()

        response = self.client.get("/cms-guide-test/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "صفحه راهنمای آزمایشی")
        self.assertEqual(content_page.get_url(), "/cms-guide-test/")

    def test_project_permission_policies_are_registered_for_wagtail(self):
        self.assertIsInstance(
            policy_registry.get_by_type(Page), StaffPagePermissionPolicy
        )
        self.assertIsInstance(
            policy_registry.get_by_type(Collection), StaffCollectionManagementPermissionPolicy
        )
        self.assertIsInstance(
            policy_registry.get_by_type(get_image_model()),
            StaffCollectionOwnershipPermissionPolicy,
        )
        self.assertIsInstance(
            policy_registry.get_by_type(get_document_model()),
            StaffCollectionOwnershipPermissionPolicy,
        )

    def test_active_staff_superuser_can_open_homepage_editor(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username="wagtail-admin",
            email="wagtail-admin@example.invalid",
            password="test-password-only",
        )
        self.client.force_login(admin_user)

        homepage = HomePage.objects.get(slug="home")
        response = self.client.get(
            reverse("wagtailadmin_pages:edit", args=(homepage.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hero_title")
        self.assertContains(response, "hero_description")

    def test_wagtail_admin_login_route_is_available(self):
        response = self.client.get(reverse("wagtailadmin_login"))
        self.assertEqual(response.status_code, 200)

    def test_staff_users_can_be_assigned_wagtail_groups(self):
        creation_form = CMSUserCreationForm()
        edit_form = CMSUserEditForm()
        self.assertIn("wagtail_groups", creation_form.fields)
        self.assertIn("wagtail_groups", edit_form.fields)
        self.assertTrue(creation_form.fields["is_staff"].initial)
        self.assertIn("is_staff", edit_form.fields)
        self.assertNotIn("is_staff", CMSUserEditForm(editing_self=True).fields)
        self.assertNotIn("groups", creation_form.fields)
        self.assertNotIn("groups", edit_form.fields)
        self.assertEqual(
            CMSUserFilterSet().filters["group"].field_name,
            "wagtail_groups",
        )

    def test_wagtail_group_permissions_use_the_separate_membership(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="cms-editor",
            password="test-password-only",
            is_staff=True,
        )
        group = Group.objects.create(name="CMS Editors")
        user.wagtail_groups.add(group)

        page_content_type = ContentType.objects.get_for_model(Page)
        permission = Permission.objects.get(
            content_type=page_content_type,
            codename="add_page",
        )
        root = Page.objects.get(depth=1)
        root.owner = user
        root.save(update_fields=["owner"])
        GroupPagePermission.objects.create(
            group=group,
            page=root,
            permission=permission,
        )

        self.assertTrue(
            GroupPagePermission.objects.filter(
                group__user=user,
                page=root,
                permission=permission,
            ).exists()
        )
        standard_permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Group),
            codename="view_group",
        )
        group.permissions.add(standard_permission)
        self.assertIn(
            f"{standard_permission.content_type.app_label}.{standard_permission.codename}",
            WagtailGroupPermissionsBackend().get_group_permissions(user),
        )
        page_policy = StaffPagePermissionPolicy()
        self.assertIn(user, page_policy.users_with_any_permission({"add"}))
        self.assertIn(
            user,
            page_policy.users_with_any_permission_for_instance({"change"}, root),
        )

    def test_wagtail_media_collection_permissions_use_wagtail_groups(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="cms-media-editor",
            password="test-password-only",
            is_staff=True,
        )
        group = Group.objects.create(name="CMS Media Editors")
        user.wagtail_groups.add(group)
        root_collection = Collection.add_root(name="CMS Media Root")
        child_collection = root_collection.add_child(name="CMS Images")
        content_type = ContentType.objects.get_for_model(Collection)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename="change_collection",
            defaults={"name": "Can change collection"},
        )
        GroupCollectionPermission.objects.create(
            group=group,
            collection=root_collection,
            permission=permission,
        )
        policy = StaffCollectionManagementPermissionPolicy(Collection)
        self.assertIn(child_collection, policy._descendants_with_perm(user, "change"))
        self.assertIn(
            user,
            policy.users_with_any_permission_for_instance({"change"}, child_collection),
        )

        media_models = (
            (get_image_model(), "add_image"),
            (get_document_model(), "add_document"),
        )
        # Wagtail caches collection permissions on the user instance. Populate
        # every media permission before the first policy lookup, as happens in
        # normal group setup, then verify both policies against that cache.
        for model, action in media_models:
            permission = Permission.objects.get(
                content_type=ContentType.objects.get_for_model(model),
                codename=action,
            )
            GroupCollectionPermission.objects.create(
                group=group,
                collection=root_collection,
                permission=permission,
            )

        for model, action in media_models:
            model_policy = policy_registry.get_by_type(model)
            diagnostic = (
                f"model={model._meta.label_lower}; "
                f"auth_model={model_policy.auth_model._meta.label_lower}; "
                f"authenticated={user.is_authenticated}; active={user.is_active}; "
                f"wagtail_groups={list(user.wagtail_groups.values_list('name', flat=True))}; "
                f"expected_codename={action}; "
                f"policy_codenames={model_policy._get_permission_codenames({'add'})}; "
                f"cached_permissions={list(model_policy.get_cached_permissions_for_user(user))}; "
                f"loaded_permissions={list(model_policy.get_all_permissions_for_user(user).values_list('permission__codename', flat=True))}"
            )
            self.assertTrue(model_policy.user_has_permission(user, "add"), diagnostic)
            self.assertIn(user, model_policy.users_with_any_permission({"add"}))
