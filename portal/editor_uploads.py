"""Secure, staff-only image upload endpoint for the catalog rich-text editor."""

from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}


@require_POST
def editor_image_upload(request):
    """Validate, decode, and re-encode an image before storing it."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_staff:
        return JsonResponse({"error": "Staff authentication is required."}, status=403)

    uploaded = request.FILES.get("upload") or request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"error": "Choose an image to upload."}, status=400)
    if uploaded.size > MAX_UPLOAD_BYTES:
        return JsonResponse({"error": "Images must be 5 MB or smaller."}, status=413)

    try:
        with Image.open(uploaded) as image:
            if image.format not in ALLOWED_FORMATS:
                return JsonResponse(
                    {"error": "Use a PNG, JPEG, WebP, or GIF image."}, status=415
                )
            if image.width < 1 or image.height < 1 or image.width * image.height > MAX_PIXELS:
                return JsonResponse(
                    {"error": "Image dimensions exceed the supported limit."}, status=413
                )
            image.verify()

        uploaded.seek(0)
        with Image.open(uploaded) as image:
            image = ImageOps.exif_transpose(image)
            has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            output = BytesIO()
            image.save(output, format="PNG", optimize=True)
            payload = output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return JsonResponse({"error": "The uploaded file is not a valid image."}, status=400)

    if len(payload) > MAX_OUTPUT_BYTES:
        return JsonResponse(
            {"error": "The processed image is too large. Resize it and try again."},
            status=413,
        )

    name = default_storage.save(
        "editor_uploads/" + uuid4().hex + ".png",
        ContentFile(payload),
    )
    url = default_storage.url(name)
    response = JsonResponse(
        {"location": url, "uploaded": 1, "fileName": name.rsplit("/", 1)[-1], "url": url}
    )
    response["Cache-Control"] = "no-store"
    return response
