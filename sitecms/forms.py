from django import forms
from django.contrib.auth.models import Group as AuthGroup
from wagtail.users.forms import UserCreationForm, UserEditForm


class CMSUserCreationForm(UserCreationForm):
    wagtail_groups = forms.ModelMultipleChoiceField(
        queryset=AuthGroup.objects.order_by("name"),
        required=False,
        label="گروه‌های دسترسی Wagtail",
        help_text=(
            "گروه‌های این بخش مجوزهای صفحات، تصاویر و اسناد Wagtail را کنترل می‌کنند؛ "
            "گروه‌های کارکنان پروژه جداگانه باقی می‌مانند."
        ),
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta(UserCreationForm.Meta):
        fields = (UserCreationForm.Meta.fields - {"groups"}) | {"wagtail_groups"}
        widgets = {
            **UserCreationForm.Meta.widgets,
            "wagtail_groups": forms.CheckboxSelectMultiple,
        }


class CMSUserEditForm(UserEditForm):
    wagtail_groups = forms.ModelMultipleChoiceField(
        queryset=AuthGroup.objects.order_by("name"),
        required=False,
        label="گروه‌های دسترسی Wagtail",
        help_text=(
            "گروه‌های این بخش مجوزهای صفحات، تصاویر و اسناد Wagtail را کنترل می‌کنند؛ "
            "گروه‌های کارکنان پروژه جداگانه باقی می‌مانند."
        ),
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta(UserEditForm.Meta):
        fields = (UserEditForm.Meta.fields - {"groups"}) | {"wagtail_groups"}
        widgets = {
            **UserEditForm.Meta.widgets,
            "wagtail_groups": forms.CheckboxSelectMultiple,
        }
