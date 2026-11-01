import uuid
from pathlib import Path

from django.core.exceptions import ValidationError


MAX_AVATAR_SIZE = 5 * 1024 * 1024


def validate_avatar_size(image):
    if image and image.size > MAX_AVATAR_SIZE:
        raise ValidationError("حجم تصویر نمایه نباید بیشتر از ۵ مگابایت باشد.")


def avatar_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    return f"avatars/{uuid.uuid4().hex}{suffix}"
