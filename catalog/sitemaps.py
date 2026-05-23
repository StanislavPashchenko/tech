from bisect import bisect_right
from collections import defaultdict

from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import Article, Breakdown, BreakdownGroup, Category, Product
from .views import _get_article_slug, _get_breakdown_slug, _get_product_slug


LANGUAGES = ("ru", "ua", "en")


class BreakdownSitemapItems:
    """Sequence-like container that keeps Django sitemap pagination lazy."""

    def __init__(self, entries):
        self._entries = entries
        self._entry_offsets = []
        total = 0
        for entry in entries:
            total += entry["count"]
            self._entry_offsets.append(total)
        self._total = total

    def __len__(self):
        return self._total

    def __iter__(self):
        for entry in self._entries:
            product = entry["product"]
            for breakdown in entry["breakdowns"]:
                for lang in LANGUAGES:
                    yield (lang, product, breakdown)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(self._total)
            if step != 1:
                return [self[index] for index in range(start, stop, step)]
            return self._slice(start, stop)

        index = int(key)
        if index < 0:
            index += self._total
        if index < 0 or index >= self._total:
            raise IndexError("Breakdown sitemap item index out of range")
        return self._item_at(index)

    def _slice(self, start, stop):
        if start >= stop:
            return []

        result = []
        entry_index = bisect_right(self._entry_offsets, start)
        current_index = start

        while current_index < stop and entry_index < len(self._entries):
            previous_offset = 0 if entry_index == 0 else self._entry_offsets[entry_index - 1]
            entry = self._entries[entry_index]
            breakdowns = entry["breakdowns"]
            relative_index = current_index - previous_offset
            breakdown_index, language_index = divmod(relative_index, len(LANGUAGES))

            while breakdown_index < len(breakdowns) and current_index < stop:
                breakdown = breakdowns[breakdown_index]
                while language_index < len(LANGUAGES) and current_index < stop:
                    result.append((LANGUAGES[language_index], entry["product"], breakdown))
                    current_index += 1
                    language_index += 1
                breakdown_index += 1
                language_index = 0

            entry_index += 1

        return result

    def _item_at(self, index):
        entry_index = bisect_right(self._entry_offsets, index)
        previous_offset = 0 if entry_index == 0 else self._entry_offsets[entry_index - 1]
        entry = self._entries[entry_index]
        relative_index = index - previous_offset
        breakdown_index, language_index = divmod(relative_index, len(LANGUAGES))
        return (LANGUAGES[language_index], entry["product"], entry["breakdowns"][breakdown_index])


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
        breakdowns_by_group = defaultdict(list)
        for breakdown in Breakdown.objects.only(
            "id",
            "breakdown_group_id",
            "title",
            "description",
            "title_ua",
            "description_ua",
            "title_en",
            "description_en",
        ).order_by("id").iterator(chunk_size=2000):
            breakdowns_by_group[breakdown.breakdown_group_id].append(breakdown)

        generic_group_ids_by_category = defaultdict(list)
        brand_group_ids_by_category_brand = defaultdict(list)
        for group in BreakdownGroup.objects.order_by("id").values("id", "category_id", "brand_id"):
            if group["brand_id"] is None:
                generic_group_ids_by_category[group["category_id"]].append(group["id"])
            else:
                brand_group_ids_by_category_brand[(group["category_id"], group["brand_id"])].append(group["id"])

        additional_group_ids_by_product = defaultdict(list)
        for product_id, breakdown_group_id in Product.breakdown_groups.through.objects.order_by(
            "product_id",
            "breakdowngroup_id",
        ).values_list("product_id", "breakdowngroup_id"):
            additional_group_ids_by_product[product_id].append(breakdown_group_id)

        entries = []
        products = Product.objects.select_related("category").only(
            "id",
            "category_id",
            "category__id_name",
            "brand_id",
            "breakdown_group_id",
            "name_ru",
            "name_ua",
            "name_en",
        ).order_by("id").iterator(chunk_size=1000)
        for product in products:
            group_ids = set(generic_group_ids_by_category.get(product.category_id, ()))
            if product.breakdown_group_id:
                group_ids.add(product.breakdown_group_id)
            group_ids.update(additional_group_ids_by_product.get(product.id, ()))
            if product.brand_id:
                group_ids.update(
                    brand_group_ids_by_category_brand.get((product.category_id, product.brand_id), ())
                )

            product_breakdowns = []
            for group_id in sorted(group_ids):
                product_breakdowns.extend(breakdowns_by_group.get(group_id, ()))

            if product_breakdowns:
                entries.append(
                    {
                        "product": product,
                        "breakdowns": tuple(product_breakdowns),
                        "count": len(product_breakdowns) * len(LANGUAGES),
                    }
                )

        return BreakdownSitemapItems(entries)

    def location(self, item):
        lang, product, breakdown = item
        return reverse(
            "breakdown_detail",
            kwargs={
                "lang": lang,
                "section_id": product.category.id_name,
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
