from wagtail.users.views.users import UserViewSet as WagtailUserViewSet

from .forms import CMSUserCreationForm, CMSUserEditForm


class UserViewSet(WagtailUserViewSet):
    """Expose Wagtail-specific auth groups alongside the project's staff groups."""

    def get_form_class(self, for_update=False):
        if for_update:
            return CMSUserEditForm
        return CMSUserCreationForm
