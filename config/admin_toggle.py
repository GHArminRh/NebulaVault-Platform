"""Secure, reusable quick toggles for editable BooleanFields in Django Admin."""

import json

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST


# Privilege-related flags must remain on the normal, fully validated edit form.
PROTECTED_BOOLEAN_FIELDS = {"is_staff", "is_superuser"}


@staff_member_required
@require_POST
def toggle_boolean_field(request):
    """Toggle one registered admin object's editable boolean field."""
    if not request.user.is_active:
        return JsonResponse({"error": "Your account is inactive."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        app_label = str(payload.get("app_label", ""))
        model_name = str(payload.get("model_name", ""))
        object_id = str(payload.get("object_id", ""))
        field_name = str(payload.get("field_name", ""))
        desired_value = payload.get("value")
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not all((app_label, model_name, object_id, field_name)) or type(desired_value) is not bool:
        return JsonResponse({"error": "Invalid toggle parameters."}, status=400)

    model = apps.get_model(app_label, model_name, require_ready=True)
    if model is None or model not in admin.site._registry:
        return JsonResponse({"error": "This model is not managed by this admin site."}, status=404)

    model_admin = admin.site._registry[model]
    try:
        field = model._meta.get_field(field_name)
    except Exception:
        return JsonResponse({"error": "Unknown field."}, status=400)

    if (
        not field.get_internal_type() == "BooleanField"
        or not field.editable
        or field.primary_key
        or field_name in PROTECTED_BOOLEAN_FIELDS
        or field_name in getattr(model_admin, "readonly_fields", ())
        or field_name not in model_admin.get_list_display(request)
    ):
        return JsonResponse({"error": "This field cannot be toggled here."}, status=400)

    if not model_admin.has_change_permission(request):
        return JsonResponse({"error": "You do not have permission to change this object."}, status=403)

    with transaction.atomic():
        obj = model_admin.get_object(request, object_id)
        if obj is None:
            return JsonResponse({"error": "Object not found."}, status=404)
        if not model_admin.has_change_permission(request, obj):
            return JsonResponse({"error": "You do not have permission to change this object."}, status=403)
        if field_name == "is_active" and not desired_value and obj.pk == request.user.pk and model is type(request.user):
            return JsonResponse({"error": "You cannot deactivate your own account here."}, status=400)

        setattr(obj, field_name, desired_value)
        obj.save(update_fields=[field_name])

    return JsonResponse({"ok": True, "value": desired_value, "label": "Yes" if desired_value else "No"})
