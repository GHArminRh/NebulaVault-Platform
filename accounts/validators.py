import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image


MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_AVATAR_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_avatar_size(image):
    if not image:
        return
    if image.size > MAX_AVATAR_SIZE:
        raise ValidationError("حجم تصویر نمایه نباید بیشتر از ۵ مگابایت باشد.")
    try:
        image.seek(0)
        with Image.open(image) as opened:
            if opened.format not in ALLOWED_AVATAR_FORMATS:
                raise ValidationError("فرمت تصویر نمایه باید JPG، PNG یا WEBP باشد.")
            opened.verify()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("فایل بارگذاری‌شده یک تصویر معتبر نیست.") from exc
    finally:
        try:
            image.seek(0)
        except Exception:
            pass


def avatar_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    return f"avatars/{uuid.uuid4().hex}{suffix}"
