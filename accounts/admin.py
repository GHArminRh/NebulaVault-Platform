from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import AccountEmailLog, Customer


class CustomerAdminForm(forms.ModelForm):
    username = forms.CharField(required=False, max_length=150)

    class Meta:
        model = Customer
        fields = "__all__"

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        local_part, separator, domain = email.rpartition("@")
        if separator:
            email = f"{local_part}@{domain.lower()}"
        return email

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").strip()
        username = (cleaned.get("username") or "").strip()

        # On the admin add form, generate a username from the email local-part
        # if the field is blank. The accompanying JS fills it live as the
        # administrator types the email address.
        if not username and email and "@" in email:
            base = email.rsplit("@", 1)[0].strip()
            if base:
                candidate = base[:150]
                suffix = 2
                queryset = Customer.objects.all()
                if self.instance.pk:
                    queryset = queryset.exclude(pk=self.instance.pk)
                while queryset.filter(username__iexact=candidate).exists():
                    tail = str(suffix)
                    candidate = f"{base[:150 - len(tail)]}{tail}"
                    suffix += 1
                cleaned["username"] = candidate

        if username and Customer.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            # If the supplied value is the generated value, let it be replaced
            # by a unique suffix rather than forcing the admin to type one.
            if email and "@" in email and username.casefold() == email.rsplit("@", 1)[0].strip().casefold():
                base = email.rsplit("@", 1)[0].strip()
                candidate = base[:150]
                suffix = 2
                while Customer.objects.filter(username__iexact=candidate).exclude(pk=self.instance.pk).exists():
                    tail = str(suffix)
                    candidate = f"{base[:150 - len(tail)]}{tail}"
                    suffix += 1
                cleaned["username"] = candidate
            else:
                self.add_error("username", ValidationError("This username is already in use. Please choose another."))
        return cleaned


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    list_display = ("email", "username", "first_name", "last_name", "is_active", "date_joined")
    list_filter = ("is_active", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined")
    ordering = ("-date_joined",)

    class Media:
        js = ("accounts/admin_customer_username.js",)


@admin.register(AccountEmailLog)
class AccountEmailLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "purpose", "status", "sent_at", "expires_at", "failed_attempts")
    list_filter = ("purpose", "status", "created_at")
    search_fields = ("recipient", "customer__email", "customer__username")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = tuple(field.name for field in AccountEmailLog._meta.fields)
    exclude = ("code_hash",)
