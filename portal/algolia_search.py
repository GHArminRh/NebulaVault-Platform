"""Algolia indexing and signal handlers for public Nebula Vault content."""

import logging
import re
import unicodedata
from functools import lru_cache
from html import unescape

from algoliasearch.search.client import SearchClientSync
from django.conf import settings
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from blog.models import BlogPost
from catalog.models import Product, Release

logger = logging.getLogger(__name__)


def normalize_search_text(value):
    """Normalize common Persian/Arabic variants, diacritics and half-spaces."""
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = value.translate(
        str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "ـ": ""})
    )
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = value.replace("\u200c", " ").replace("\u200d", " ")
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def get_algolia_client():
    app_id = getattr(settings, "ALGOLIA_APP_ID", "")
    admin_key = getattr(settings, "ALGOLIA_ADMIN_API_KEY", "")
    if not app_id or not admin_key:
        return None
    return SearchClientSync(app_id, admin_key)


def _plain_text(value, limit=2800):
    return normalize_search_text(unescape(strip_tags(value or "")))[:limit]


def _save(index_name, record):
    client = get_algolia_client()
    if client is None:
        return
    try:
        client.save_object(index_name=index_name, body=record)
    except Exception:
        logger.exception("Algolia indexing failed for %s/%s", index_name, record.get("objectID"))


def _delete(index_name, object_id):
    client = get_algolia_client()
    if client is None:
        return
    try:
        client.delete_object(index_name=index_name, object_id=str(object_id))
    except Exception:
        logger.exception("Algolia deletion failed for %s/%s", index_name, object_id)


def product_record(product):
    releases = list(
        product.releases.filter(is_published=True)
        .values("version", "platform", "architecture")[:20]
    )
    platforms = sorted({item["platform"] for item in releases if item["platform"]})
    versions = [item["version"] for item in releases if item["version"]]
    description = _plain_text(product.description)
    search_text = normalize_search_text(
        " ".join([product.name, product.slug, description, " ".join(platforms), " ".join(versions)])
    )
    return {
        "objectID": str(product.pk),
        "type": "product",
        "title": product.name,
        "name": product.name,
        "slug": product.slug,
        "description": description,
        "platforms": platforms,
        "versions": versions,
        "searchText": search_text,
        "url": reverse("portal:product_detail", kwargs={"slug": product.slug}),
    }


def blog_post_is_public(post):
    return (
        post.status == post.Status.PUBLISHED
        and post.published_at is not None
        and post.published_at <= timezone.now()
    )


def blog_post_record(post):
    excerpt = _plain_text(post.excerpt, limit=500)
    content = _plain_text(post.content)
    tags = list(post.tags.order_by("name").values_list("name", flat=True))
    category = normalize_search_text(post.category)
    search_text = normalize_search_text(
        " ".join([post.title, excerpt, content, category, " ".join(tags)])
    )
    return {
        "objectID": str(post.pk),
        "type": "article",
        "title": post.title,
        "slug": post.slug,
        "excerpt": excerpt,
        "content": content,
        "category": category,
        "tags": [normalize_search_text(tag) for tag in tags],
        "searchText": search_text,
        "publishedAt": post.published_at.isoformat(),
        "url": reverse("blog:post_detail", kwargs={"slug": post.slug}),
    }


def sync_product(product):
    if product.is_active:
        _save(settings.ALGOLIA_PRODUCTS_INDEX, product_record(product))
    else:
        _delete(settings.ALGOLIA_PRODUCTS_INDEX, product.pk)


def sync_product_by_id(product_id):
    product = Product.objects.filter(pk=product_id).first()
    if product:
        sync_product(product)


def sync_blog_post(post):
    if blog_post_is_public(post):
        _save(settings.ALGOLIA_ARTICLES_INDEX, blog_post_record(post))
    else:
        _delete(settings.ALGOLIA_ARTICLES_INDEX, post.pk)


def sync_blog_post_by_id(post_id):
    post = BlogPost.objects.filter(pk=post_id).first()
    if post:
        sync_blog_post(post)
    else:
        _delete(settings.ALGOLIA_ARTICLES_INDEX, post_id)


@receiver(post_save, sender=Product)
def product_saved(sender, instance, **kwargs):
    transaction.on_commit(lambda pk=instance.pk: sync_product_by_id(pk))


@receiver(post_delete, sender=Product)
def product_deleted(sender, instance, **kwargs):
    transaction.on_commit(
        lambda pk=instance.pk: _delete(settings.ALGOLIA_PRODUCTS_INDEX, pk)
    )


@receiver(post_save, sender=Release)
def release_saved(sender, instance, **kwargs):
    transaction.on_commit(lambda pk=instance.product_id: sync_product_by_id(pk))


@receiver(post_delete, sender=Release)
def release_deleted(sender, instance, **kwargs):
    transaction.on_commit(lambda pk=instance.product_id: sync_product_by_id(pk))


@receiver(post_save, sender=BlogPost)
def blog_post_saved(sender, instance, **kwargs):
    transaction.on_commit(lambda pk=instance.pk: sync_blog_post_by_id(pk))


@receiver(post_delete, sender=BlogPost)
def blog_post_deleted(sender, instance, **kwargs):
    transaction.on_commit(
        lambda pk=instance.pk: _delete(settings.ALGOLIA_ARTICLES_INDEX, pk)
    )


@receiver(m2m_changed, sender=BlogPost.tags.through)
def blog_post_tags_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        transaction.on_commit(lambda pk=instance.pk: sync_blog_post_by_id(pk))
