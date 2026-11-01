from django.conf import settings
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
from .models import HomePage
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
        homepage = HomePage.objects.create(
            page_ptr_id=base_home.pk,
            hero_title="عنوان قابل ویرایش از Wagtail",
            hero_highlight="تأکید قابل ویرایش",
        )
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

    def test_wagtail_admin_login_route_is_available(self):
        response = self.client.get(reverse("wagtailadmin_login"))
        self.assertEqual(response.status_code, 200)

    def test_staff_users_can_be_assigned_wagtail_groups(self):
        self.assertIn("wagtail_groups", CMSUserCreationForm().fields)
        self.assertIn("wagtail_groups", CMSUserEditForm().fields)

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
        self.assertIn(
            f"{permission.content_type.app_label}.{permission.codename}",
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

        for model, action in (
            (get_image_model(), "add_image"),
            (get_document_model(), "add_document"),
        ):
            permission = Permission.objects.get(
                content_type=ContentType.objects.get_for_model(model),
                codename=action,
            )
            GroupCollectionPermission.objects.create(
                group=group,
                collection=root_collection,
                permission=permission,
            )
            model_policy = policy_registry.get_by_type(model)
            self.assertTrue(model_policy.user_has_permission(user, "add"))
            self.assertIn(user, model_policy.users_with_any_permission({"add"}))
