"""Reusable, safe editorial blocks for the Nebula Vault Wagtail CMS."""
from django.core.validators import RegexValidator
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


INTERNAL_OR_HTTPS_URL = RegexValidator(
    regex=r"^(?:#|/(?!/)|https://)\S*$",
    message="از نشانی داخلی، لنگر صفحه یا پیوند HTTPS استفاده کنید.",
)


class EditorialCardBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=120, label="عنوان")
    text = blocks.TextBlock(max_length=500, label="توضیحات")
    link_label = blocks.CharBlock(max_length=80, required=False, label="متن پیوند")
    link_url = blocks.CharBlock(
        max_length=300,
        required=False,
        validators=[INTERNAL_OR_HTTPS_URL],
        label="نشانی پیوند",
    )

    class Meta:
        label = "کارت محتوا"


class CallToActionBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(max_length=100, required=False, label="متن بالایی")
    title = blocks.CharBlock(max_length=180, label="عنوان")
    text = blocks.TextBlock(max_length=500, required=False, label="توضیحات")
    button_label = blocks.CharBlock(max_length=80, label="متن دکمه")
    button_url = blocks.CharBlock(
        max_length=300,
        validators=[INTERNAL_OR_HTTPS_URL],
        label="نشانی دکمه",
    )

    class Meta:
        label = "دعوت به اقدام"
        template = "sitecms/blocks/call_to_action.html"


class QuoteBlock(blocks.StructBlock):
    quote = blocks.TextBlock(max_length=1000, label="متن نقل‌قول")
    attribution = blocks.CharBlock(max_length=120, required=False, label="گوینده")

    class Meta:
        label = "نقل‌قول"
        template = "sitecms/blocks/quote.html"


class NoticeBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=120, label="عنوان")
    text = blocks.TextBlock(max_length=1000, label="متن")
    tone = blocks.ChoiceBlock(
        choices=[
            ("info", "اطلاع‌رسانی"),
            ("success", "موفقیت"),
            ("warning", "هشدار"),
        ],
        default="info",
        label="نوع نمایش",
    )

    class Meta:
        label = "اطلاعیه"
        template = "sitecms/blocks/notice.html"



class FeatureItemBlock(blocks.StructBlock):
    icon = blocks.CharBlock(max_length=8, required=False, default="◇", label="نماد")
    title = blocks.CharBlock(max_length=120, label="عنوان")
    text = blocks.TextBlock(max_length=400, label="توضیحات")
    link_label = blocks.CharBlock(max_length=80, required=False, label="متن پیوند")
    link_url = blocks.CharBlock(
        max_length=300,
        required=False,
        validators=[INTERNAL_OR_HTTPS_URL],
        label="نشانی پیوند",
    )

    class Meta:
        label = "ویژگی"


class FeatureGridBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(max_length=100, label="متن بالایی")
    title = blocks.CharBlock(max_length=180, label="عنوان")
    description = blocks.CharBlock(max_length=300, required=False, label="توضیحات")
    items = blocks.ListBlock(
        FeatureItemBlock(),
        min_num=1,
        max_num=4,
        label="کارت‌های ویژگی",
    )

    class Meta:
        label = "بخش ویژگی‌ها"
        template = "sitecms/blocks/features.html"


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock(max_length=240, label="پرسش")
    answer = blocks.TextBlock(max_length=1200, label="پاسخ")

    class Meta:
        label = "پرسش و پاسخ"


class FAQBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(max_length=100, label="متن بالایی")
    title = blocks.CharBlock(max_length=180, label="عنوان")
    description = blocks.CharBlock(max_length=300, required=False, label="توضیحات")
    items = blocks.ListBlock(
        FAQItemBlock(),
        min_num=1,
        max_num=12,
        label="پرسش‌ها",
    )

    class Meta:
        label = "پرسش‌های متداول"
        template = "sitecms/blocks/faq.html"


class ProofItemBlock(blocks.StructBlock):
    number = blocks.CharBlock(max_length=8, label="شماره")
    label = blocks.CharBlock(max_length=100, label="متن")

    class Meta:
        label = "مورد نوار اعتماد"


class ProofStripBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        max_length=120,
        required=False,
        default="یک تجربه‌ی یکپارچه",
        label="عنوان",
    )
    items = blocks.ListBlock(
        ProofItemBlock(),
        min_num=1,
        max_num=6,
        label="موارد",
    )

    class Meta:
        label = "نوار اعتماد"
        template = "sitecms/blocks/proof_strip.html"

class NebulaContentBlock(blocks.StreamBlock):
    heading = blocks.CharBlock(
        max_length=180,
        form_classname="title",
        label="عنوان بخش",
        template="sitecms/blocks/heading.html",
    )
    rich_text = blocks.RichTextBlock(
        features=[
            "h2", "h3", "h4", "bold", "italic", "link", "ul", "ol",
            "blockquote", "hr",
        ],
        label="متن قالب‌بندی‌شده",
        template="sitecms/blocks/rich_text.html",
    )
    image = ImageChooserBlock(
        label="تصویر",
        template="sitecms/blocks/image.html",
    )
    cards = blocks.ListBlock(
        EditorialCardBlock(),
        min_num=1,
        max_num=6,
        label="مجموعه کارت‌ها",
        template="sitecms/blocks/cards.html",
    )
    call_to_action = CallToActionBlock()
    feature_grid = FeatureGridBlock()
    faq = FAQBlock()
    proof_strip = ProofStripBlock()
    quote = QuoteBlock()
    notice = NoticeBlock()

    class Meta:
        label = "بلوک‌های محتوایی نبیولا"
        icon = "placeholder"
