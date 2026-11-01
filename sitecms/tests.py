from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounts.backends import WagtailGroupPermissionsBackend
from wagtail.models import GroupPagePermission, Page, Site

from .forms import CMSUserCreationForm, CMSUserEditForm
from .models import HomePage


class WagtailIntegrationTests(TestCase):
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
