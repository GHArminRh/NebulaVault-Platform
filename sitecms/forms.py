from django import forms
from django.contrib.auth.models import Group as AuthGroup
from wagtail.users.forms import UserCreationForm, UserEditForm


class CMSUserCreationForm(UserCreationForm):
    is_staff = forms.BooleanField(
        initial=True,
        required=False,
        label="دسترسی به پنل مدیریت",
        help_text="برای ورود این حساب به Wagtail و بخش مدیریت، این گزینه باید فعال باشد.",
    )
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
        fields = (UserCreationForm.Meta.fields - {"groups"}) | {"wagtail_groups", "is_staff"}
        widgets = {
            **UserCreationForm.Meta.widgets,
            "wagtail_groups": forms.CheckboxSelectMultiple,
        }


class CMSUserEditForm(UserEditForm):
    is_staff = forms.BooleanField(
        required=False,
        label="دسترسی به پنل مدیریت",
        help_text="غیرفعال‌کردن این گزینه، دسترسی مدیریتی این کاربر را می‌بندد.",
    )

    def __init__(self, *args, **kwargs):
        editing_self = kwargs.get("editing_self", False)
        super().__init__(*args, **kwargs)
        if editing_self:
            self.fields.pop("is_staff", None)
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
        fields = (UserEditForm.Meta.fields - {"groups"}) | {"wagtail_groups", "is_staff"}
        widgets = {
            **UserEditForm.Meta.widgets,
            "wagtail_groups": forms.CheckboxSelectMultiple,
        }
