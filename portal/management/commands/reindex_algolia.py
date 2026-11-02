from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from blog.models import BlogPost
from catalog.models import Product
from portal.algolia_search import (
    blog_post_is_public,
    blog_post_record,
    get_algolia_client,
    product_record,
)


INDEX_SETTINGS = {
    "searchableAttributes": [
        "unordered(title)",
        "unordered(name)",
        "unordered(category)",
        "unordered(tags)",
        "unordered(description)",
        "unordered(excerpt)",
        "content",
        "searchText",
    ],
    "attributesForFaceting": ["type", "category", "tags", "platforms"],
    "typoTolerance": True,
    "removeWordsIfNoResults": "allOptional",
    "highlightPreTag": "<mark>",
    "highlightPostTag": "</mark>",
}


class Command(BaseCommand):
    help = "Rebuild the public Algolia product and article indexes."

    def handle(self, *args, **options):
        client = get_algolia_client()
        if client is None:
            raise CommandError(
                "Set ALGOLIA_APP_ID and ALGOLIA_ADMIN_API_KEY before reindexing."
            )

        product_index = settings.ALGOLIA_PRODUCTS_INDEX
        article_index = settings.ALGOLIA_ARTICLES_INDEX
        for index_name in (product_index, article_index):
            # Create the index first so the initial setup also works on a new Algolia app.
            bootstrap_task = client.save_object(
                index_name=index_name,
                body={"objectID": "__nebula_bootstrap__"},
            )
            client.wait_for_task(index_name=index_name, task_id=bootstrap_task.task_id)
            clear_task = client.clear_objects(index_name=index_name)
            client.wait_for_task(index_name=index_name, task_id=clear_task.task_id)
            settings_task = client.set_settings(
                index_name=index_name, index_settings=INDEX_SETTINGS
            )
            client.wait_for_task(index_name=index_name, task_id=settings_task.task_id)

        products = [
            product_record(product)
            for product in Product.objects.filter(is_active=True).prefetch_related("releases")
        ]
        articles = [
            blog_post_record(post)
            for post in BlogPost.objects.filter(
                status=BlogPost.Status.PUBLISHED,
                published_at__lte=timezone.now(),
            ).prefetch_related("tags")
            if blog_post_is_public(post)
        ]

        if products:
            client.save_objects(index_name=product_index, objects=products, wait_for_tasks=True)
        if articles:
            client.save_objects(index_name=article_index, objects=articles, wait_for_tasks=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Algolia indexes rebuilt: {len(products)} products, {len(articles)} articles."
            )
        )
