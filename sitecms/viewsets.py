from django.contrib.auth.models import Group as AuthGroup
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy

from wagtail.users.views.users import (
    GroupFilter,
    UserFilterSet as WagtailUserFilterSet,
    UserViewSet as WagtailUserViewSet,
)

from .forms import CMSUserCreationForm, CMSUserEditForm


class CMSUserFilterSet(WagtailUserFilterSet):
    """Filter staff users by their Wagtail memberships, not staff groups."""

    def __init__(
        self, data=None, queryset=None, *, request=None, prefix=None, is_searching=False
    ):
        super().__init__(
            data,
            queryset,
            request=request,
            prefix=prefix,
            is_searching=is_searching,
        )
        self.filters["group"] = GroupFilter(
            field_name="wagtail_groups",
            queryset=AuthGroup.objects.all(),
            label=gettext_lazy("Wagtail groups"),
            use_subquery=is_searching,
            widget=CheckboxSelectMultiple,
        )


class UserViewSet(WagtailUserViewSet):
    """Expose Wagtail-specific auth groups alongside the project's staff groups."""

    filterset_class = CMSUserFilterSet

    def get_form_class(self, for_update=False):
        if for_update:
            return CMSUserEditForm
        return CMSUserCreationForm
