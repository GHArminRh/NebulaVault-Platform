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



# Reusable per-object JSON tools for every model registered in Django Admin.
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify


JSON_EXPORT_FORMAT = "nebula-vault-admin-json"
JSON_EXPORT_VERSION = 1
JSON_IMPORT_MAX_BYTES = 5 * 1024 * 1024
JSON_IMPORT_MAX_RECORDS = 1000
JSON_EXCLUDED_FIELDS = {
    "password", "last_login", "is_staff", "is_superuser",
    "groups", "user_permissions",
}


def _admin_model(app_label, model_name):
    try:
        model = apps.get_model(app_label, model_name, require_ready=True)
    except LookupError:
        return None, None
    if model is None or model not in admin.site._registry:
        return None, None
    return model, admin.site._registry[model]


def _can_view_object(request, model_admin, obj):
    return (
        model_admin.has_view_or_change_permission(request, obj)
        and model_admin.get_queryset(request).filter(pk=obj.pk).exists()
    )


def _json_safe_field_name(name):
    lowered = name.lower()
    return (
        lowered not in JSON_EXCLUDED_FIELDS
        and not any(part in lowered for part in ("password", "secret", "token", "api_key", "private_key"))
    )


@staff_member_required
def export_admin_object_json(request, app_label, model_name, object_id):
    """Download one permitted admin object as a portable JSON document."""
    if not request.user.is_active:
        raise PermissionDenied
    model, model_admin = _admin_model(app_label, model_name)
    if model is None:
        return HttpResponse("Unknown admin model.", status=404)
    obj = model_admin.get_object(request, object_id)
    if obj is None:
        return HttpResponse("Object not found.", status=404)
    if not _can_view_object(request, model_admin, obj):
        raise PermissionDenied

    fields = {}
    for field in model._meta.concrete_fields:
        if (
            field.primary_key or field.auto_created
            or field.get_internal_type() in {"FileField", "ImageField"}
            or not _json_safe_field_name(field.name)
        ):
            continue
        fields[field.name] = getattr(obj, field.attname)
    payload = {
        "format": JSON_EXPORT_FORMAT,
        "version": JSON_EXPORT_VERSION,
        "model": model._meta.label_lower,
        "pk": obj.pk,
        "fields": fields,
    }
    body = json.dumps(payload, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
    filename = f"{slugify(model._meta.model_name)}-{slugify(str(obj.pk)) or 'record'}.json"
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _import_admin_record(request, model, model_admin, record):
    if not isinstance(record, dict):
        raise ValueError("هر رکورد JSON باید یک شیء باشد.")
    if record.get("format") != JSON_EXPORT_FORMAT or record.get("version") != JSON_EXPORT_VERSION:
        raise ValueError("فرمت JSON پشتیبانی نمی‌شود یا نسخه فایل معتبر نیست.")
    if record.get("model") != model._meta.label_lower:
        raise ValueError(f"فایل متعلق به مدل {model._meta.label_lower} نیست.")
    data = record.get("fields")
    if not isinstance(data, dict):
        raise ValueError("بخش fields در فایل JSON معتبر نیست.")

    pk_field = model._meta.pk
    raw_pk = record.get("pk")
    obj = None
    if raw_pk not in (None, ""):
        try:
            typed_pk = pk_field.to_python(raw_pk)
        except (ValidationError, ValueError, TypeError) as exc:
            raise ValueError("شناسه رکورد در فایل JSON معتبر نیست.") from exc
        obj = model_admin.get_queryset(request).filter(pk=typed_pk).first()
        if obj is None and model._default_manager.filter(pk=typed_pk).exists():
            # Do not treat an existing but admin-hidden object as a new record.
            raise PermissionDenied("به این رکورد دسترسی ندارید.")

    if obj is not None:
        if not model_admin.has_change_permission(request, obj):
            raise PermissionDenied("اجازه ویرایش این رکورد را ندارید.")
    elif not model_admin.has_add_permission(request):
        raise PermissionDenied("اجازه افزودن رکورد جدید را ندارید.")

    allowed = {}
    model_fields = {field.name: field for field in model._meta.concrete_fields}
    for name, value in data.items():
        field = model_fields.get(name)
        if field is None:
            raise ValueError(f"فیلد ناشناخته در فایل JSON: {name}")
        if (
            field.primary_key or field.auto_created or not field.editable
            or field.get_internal_type() in {"FileField", "ImageField"}
            or field.name in JSON_EXCLUDED_FIELDS
            or not _json_safe_field_name(field.name)
        ):
            continue
        # ForeignKey values are represented by their raw database ID.
        try:
            allowed[field.attname] = field.to_python(value)
        except (ValidationError, ValueError, TypeError) as exc:
            raise ValueError(f"مقدار فیلد {name} معتبر نیست.") from exc

    creating = obj is None
    if creating:
        obj = model()
        # Keep the original primary key when importing a single-record export
        # into another database; a collision above intentionally updates only
        # when the current user has permission to change that object.
        if raw_pk not in (None, ""):
            setattr(obj, pk_field.attname, pk_field.to_python(raw_pk))
    for attname, value in allowed.items():
        setattr(obj, attname, value)

    if creating and hasattr(obj, "set_unusable_password") and not getattr(obj, "password", ""):
        obj.set_unusable_password()
    obj.full_clean()
    obj.save()
    return "created" if creating else "updated"


@staff_member_required
def import_admin_json(request, app_label, model_name):
    """Import one or many Nebula Vault JSON exports for a registered model."""
    if not request.user.is_active:
        raise PermissionDenied
    model, model_admin = _admin_model(app_label, model_name)
    if model is None:
        return HttpResponse("Unknown admin model.", status=404)
    if not (model_admin.has_add_permission(request) or model_admin.has_change_permission(request)):
        raise PermissionDenied

    opts = model._meta
    context = {
        **admin.site.each_context(request),
        "opts": opts,
        "title": f"Import JSON — {opts.verbose_name_plural}",
        "app_label": opts.app_label,
        "model_name": opts.model_name,
        "changelist_url": f"/admin/{opts.app_label}/{opts.model_name}/",
        "has_permission": True,
    }
    if request.method == "POST":
        uploads = request.FILES.getlist("json_files") or request.FILES.getlist("json_file")
        if not uploads:
            messages.error(request, "یک یا چند فایل JSON انتخاب کنید.")
        elif sum(upload.size for upload in uploads) > JSON_IMPORT_MAX_BYTES:
            messages.error(request, "مجموع اندازه فایل‌های JSON نباید از ۵ مگابایت بیشتر باشد.")
        else:
            try:
                records = []
                for uploaded in uploads:
                    decoded = uploaded.read().decode("utf-8-sig")
                    parsed = json.loads(decoded)
                    records.extend(parsed if isinstance(parsed, list) else [parsed])
                    if len(records) > JSON_IMPORT_MAX_RECORDS:
                        raise ValueError("حداکثر ۱۰۰۰ رکورد را می‌توان در یک عملیات وارد کرد.")
                if not records:
                    raise ValueError("فایل‌ها هیچ رکوردی ندارند.")
                created = updated = 0
                with transaction.atomic():
                    for record in records:
                        outcome = _import_admin_record(request, model, model_admin, record)
                        if outcome == "created":
                            created += 1
                        else:
                            updated += 1
                messages.success(
                    request,
                    f"واردسازی انجام شد؛ {created} رکورد جدید و {updated} رکورد به‌روزرسانی شد.",
                )
                return redirect(f"/admin/{opts.app_label}/{opts.model_name}/")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, ValidationError, IntegrityError) as exc:
                messages.error(request, f"واردسازی انجام نشد: {exc}")
            except PermissionDenied:
                raise
    return render(request, "admin/json_import.html", context)
