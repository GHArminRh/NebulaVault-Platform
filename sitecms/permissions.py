from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q

from wagtail.models import (
    AbstractPage,
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
)
from wagtail.permission_policies.collections import (
    CollectionManagementPermissionPolicy,
)
from wagtail.permission_policies.pages import PagePermissionPolicy


class StaffPagePermissionPolicy(PagePermissionPolicy):
    """Use the dedicated Wagtail group relation for staff permission lookups."""

    def get_all_permissions_for_user(self, user):
        if not user.is_active or user.is_anonymous or user.is_superuser:
            return GroupPagePermission.objects.none()
        return GroupPagePermission.objects.filter(
            group__in=user.wagtail_groups.all()
        ).select_related("page", "permission")

    def users_with_any_permission(self, actions, include_superusers=True):
        actions = set(actions)
        if "change" in actions:
            actions.add("add")

        groups = GroupPagePermission.objects.filter(
            permission__codename__in=self._get_permission_codenames(actions)
        ).values_list("group_id", flat=True)

        query = Q(wagtail_groups__in=groups)
        if include_superusers:
            query |= Q(is_superuser=True)

        return (
            get_user_model()
            ._default_manager.filter(is_active=True)
            .filter(query)
            .distinct()
        )

    def users_with_any_permission_for_instance(
        self, actions, instance, include_superusers=True
    ):
        ancestors = instance.get_ancestors(inclusive=True)
        groups = GroupPagePermission.objects.filter(
            permission__codename__in=self._get_permission_codenames(actions),
            page__in=ancestors,
        ).values_list("group_id", flat=True)

        query = Q(wagtail_groups__in=groups)
        if include_superusers:
            query |= Q(is_superuser=True)

        if "change" in actions and "add" not in actions:
            add_groups = GroupPagePermission.objects.filter(
                permission__codename=self._get_permission_codename("add"),
                page__in=ancestors,
            ).values_list("group_id", flat=True)
            query |= Q(wagtail_groups__in=add_groups) & Q(pk=instance.owner_id)

        return (
            get_user_model()
            ._default_manager.filter(is_active=True)
            .filter(query)
            .distinct()
        )


class StaffCollectionManagementPermissionPolicy(CollectionManagementPermissionPolicy):
    """Use Wagtail groups, not the project's unrelated UUID staff groups."""

    @staticmethod
    def _groups_for_user(user):
        if hasattr(user, "wagtail_groups"):
            return user.wagtail_groups.all()
        return user.groups.all()

    def get_all_permissions_for_user(self, user):
        if not user.is_active or user.is_anonymous or user.is_superuser:
            return GroupCollectionPermission.objects.none()
        return GroupCollectionPermission.objects.filter(
            group__in=self._groups_for_user(user)
        ).select_related("permission", "collection")

    def _descendants_with_perm(self, user, action):
        permission = self._get_permission_objects_for_actions([action]).first()
        if permission is None:
            return Collection.objects.none()

        collection_roots = list(
            Collection.objects.filter(
                group_permissions__group__in=self._groups_for_user(user),
                group_permissions__permission=permission,
            ).values("path", "depth")
        )
        if not collection_roots:
            return Collection.objects.none()

        query = Q()
        for collection in collection_roots:
            query |= Q(
                path__startswith=collection["path"],
                depth__gt=collection["depth"],
            )
        return Collection.objects.filter(query)

    def _users_with_perm_filter(self, actions, collection=None):
        permissions = self._get_permission_objects_for_actions(actions)
        groups = Group.objects.filter(
            collection_permissions__permission__in=permissions,
        )

        if collection is not None:
            collections = collection.get_ancestors(inclusive=True)
            groups = groups.filter(collection_permissions__collection__in=collections)

        return Q(is_active=True) & (
            Q(is_superuser=True) | Q(wagtail_groups__in=groups)
        )


def register_staff_permission_policies():
    """Replace the two stock policies whose queries assume User.groups is auth.Group."""
    from wagtail.permissions import policy_registry, register_permission_policy

    register_permission_policy(AbstractPage, StaffPagePermissionPolicy())
    policy_registry.register(
        Collection,
        value=StaffCollectionManagementPermissionPolicy(Collection),
        exact_class=True,
    )
