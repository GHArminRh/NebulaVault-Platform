from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}))
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user
