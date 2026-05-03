from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import Article, Breakdown, Category, Product
from .views import _get_article_slug, _get_breakdown_slug, _get_product_slug


LANGUAGES = ("ru", "ua", "en")


class StaticViewSitemap(Sitemap):
    protocol = "https"
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return [
            ("index_lang", {"lang": lang})
            for lang in LANGUAGES
        ] + [
            ("products_index", {"lang": lang})
            for lang in LANGUAGES
        ] + [
            ("articles_index", {"lang": lang})
            for lang in LANGUAGES
        ]

    def location(self, item):
        route_name, kwargs = item
        return reverse(route_name, kwargs=kwargs)


class CategorySitemap(Sitemap):
    protocol = "https"
    priority = 0.9
    changefreq = "daily"

    def items(self):
        categories = Category.objects.order_by("id")
        return [
            (lang, category)
            for lang in LANGUAGES
            for category in categories
        ]

    def location(self, item):
        lang, category = item
        return reverse(
            "product_section",
            kwargs={"lang": lang, "section_id": category.id_name},
        )


class ProductSitemap(Sitemap):
    protocol = "https"
    priority = 0.8
    changefreq = "weekly"
    limit = 1000

    def items(self):
        products = Product.objects.select_related("category").order_by("id")
        return [
            (lang, product)
            for lang in LANGUAGES
            for product in products
        ]

    def location(self, item):
        lang, product = item
        return reverse(
            "product_detail",
            kwargs={
                "lang": lang,
                "section_id": product.category.id_name,
                "product_slug": _get_product_slug(product, lang),
            },
        )


class BreakdownSitemap(Sitemap):
    protocol = "https"
    priority = 0.7
    changefreq = "weekly"
    limit = 1000

    def items(self):
        breakdowns = list(
            Breakdown.objects.select_related("breakdown_group__category")
            .order_by("id")
        )
        primary_products = {}
        for product in (
            Product.objects.select_related("category")
            .prefetch_related("breakdown_groups")
            .order_by("id")
        ):
            if product.breakdown_group_id and product.breakdown_group_id not in primary_products:
                primary_products[product.breakdown_group_id] = product
            for group in product.breakdown_groups.all():
                if group.id not in primary_products:
                    primary_products[group.id] = product
        return [
            (lang, breakdown, primary_products.get(breakdown.breakdown_group_id))
            for lang in LANGUAGES
            for breakdown in breakdowns
        ]

    def location(self, item):
        lang, breakdown, product = item
        category = breakdown.breakdown_group.category
        if product is None:
            return reverse(
                "product_section",
                kwargs={"lang": lang, "section_id": category.id_name},
            )
        return reverse(
            "breakdown_detail",
            kwargs={
                "lang": lang,
                "section_id": category.id_name,
                "product_slug": _get_product_slug(product, lang),
                "breakdown_slug": _get_breakdown_slug(breakdown, lang),
            },
        )


class ArticleSitemap(Sitemap):
    protocol = "https"
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        now = timezone.now()
        articles = Article.objects.filter(
            is_published=True,
        ).filter(
            Q(published_at__isnull=True) | Q(published_at__lte=now)
        ).order_by("-published_at", "-created_at", "-id")
        return [
            (lang, article)
            for lang in LANGUAGES
            for article in articles
        ]
    
    def lastmod(self, item):
        _, article = item
        return article.updated_at

    def location(self, item):
        lang, article = item
        return reverse(
            "article_detail",
            kwargs={
                "lang": lang,
                "article_id": article.id,
                "article_slug": _get_article_slug(article, lang),
            },
        )


sitemaps = {
    "static": StaticViewSitemap(),
    "categories": CategorySitemap(),
    "products": ProductSitemap(),
    "breakdowns": BreakdownSitemap(),
    "articles": ArticleSitemap(),
}
