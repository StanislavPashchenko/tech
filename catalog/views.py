import re

from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from .models import Article, Breakdown, Category, Product
from .brand_utils import find_vacuum_brand_name, format_fallback_brand, get_brand_slug
from .vacuum_filters import (
    apply_section_filters,
    build_brand_choices,
    build_filter_state,
    enrich_filter_groups,
    get_filter_labels,
    get_query_string_without_page,
    get_section_filter_groups,
)

_DYNAMIC_FILTER_MIN_OPTIONS = 2
_DYNAMIC_FILTER_MAX_OPTIONS = 80
_DYNAMIC_FILTER_MIN_COVERAGE = 3
_DYNAMIC_FILTER_MAX_KEY_LENGTH = 80
_DYNAMIC_FILTER_MAX_VALUE_LENGTH = 120
_DYNAMIC_FILTER_EXCLUDED_TITLES = {
    'официальный сайт',
    'офіційний сайт',
    'official website',
    'дата добавления на e-katalog',
    'дата додавання на e-katalog',
    'date added to e-katalog',
    'маркировка производителя',
    'маркування виробника',
    'manufacturer part number',
}
_DYNAMIC_FILTER_EXCLUDED_TITLE_PARTS = (
    'отзыв полезен',
    'відгук корисний',
    'review helpful',
    'отличная модель',
    'хорошая модель',
    'чудова модель',
    'очень понравилось',
    'дуже сподобалося',
    'дуже сподобалось',
    'очень понравилась',
    'сподобалося',
    'сподобалось',
    'понравилось',
)
_DYNAMIC_FILTER_NOISE_PATTERN = re.compile(
    r'(https?://|www\.|[a-z0-9-]+\.(?:com|ua|pl|de|net|org|ru|eu|kiev|lviv)\b|→)',
    re.IGNORECASE,
)
_DYNAMIC_FILTER_PHOTO_PATTERN = re.compile(r'^(фото|photo)\s*\d+$', re.IGNORECASE)
_ERROR_CODE_PATTERN = re.compile(
    r'\b([A-Za-z]{1,4}[\s\-_]?\d{1,4}[A-Za-z]{0,3}|\d{1,4}[A-Za-z]{1,4})\b',
    re.IGNORECASE,
)

def _get_specs_for_language(product, lang):
    specs_raw = getattr(product, f'specs_{lang}')
    if isinstance(specs_raw, str):
        import json
        try:
            return json.loads(specs_raw)
        except:
            return {}
    return specs_raw or {}

def _extract_brand_from_folder(folder_name):
    if not folder_name:
        return ''
    parts = [part for part in folder_name.replace('-', '_').split('_') if part]
    if not parts:
        return ''
    return format_fallback_brand(parts[0])

def _extract_brand(product, lang):
    if getattr(product, 'brand_id', None) and getattr(product, 'brand', None):
        return product.brand.name
    if getattr(product, 'category_id', None) and getattr(product.category, 'id_name', None) == 'cleaners':
        brand = find_vacuum_brand_name(
            product.product_folder,
            [product.name_en, product.name_ru, product.name_ua],
        )
        if brand:
            return brand
    brand = _extract_brand_from_folder(product.product_folder)
    if brand:
        return brand
    for value in [product.name_en, product.name_ru, product.name_ua]:
        if not value:
            continue
        for token in value.split():
            cleaned_token = ''.join(char for char in token if char.isalpha() or char in '-_')
            if any('a' <= char.lower() <= 'z' for char in cleaned_token):
                brand = _extract_brand_from_folder(cleaned_token)
                if brand:
                    return brand
    fallback = {
        'ru': 'Без бренда',
        'ua': 'Без бренду',
        'en': 'No Brand',
    }
    return fallback.get(lang, 'No Brand')


def _normalize_filter_text(value):
    return str(value or '').strip().lower()


def _looks_like_dynamic_filter_noise(value, max_length):
    text = str(value or '').strip()
    if not text:
        return True
    if len(text) > max_length:
        return True

    normalized_text = _normalize_filter_text(text)
    if normalized_text in _DYNAMIC_FILTER_EXCLUDED_TITLES:
        return True
    if _DYNAMIC_FILTER_NOISE_PATTERN.search(text):
        return True
    if _DYNAMIC_FILTER_PHOTO_PATTERN.match(text):
        return True
    if '\n' in text and len(text.splitlines()) > 2:
        return True
    return False


def _is_dynamic_filter_key_allowed(key):
    normalized_key = _normalize_filter_text(key)
    if normalized_key in _DYNAMIC_FILTER_EXCLUDED_TITLES:
        return False
    if any(part in normalized_key for part in _DYNAMIC_FILTER_EXCLUDED_TITLE_PARTS):
        return False
    if any(token in normalized_key for token in ('модель', 'model')) and (
        ',' in normalized_key or len(normalized_key.split()) > 3
    ):
        return False
    return not _looks_like_dynamic_filter_noise(key, _DYNAMIC_FILTER_MAX_KEY_LENGTH)


def _is_dynamic_filter_value_allowed(value):
    return not _looks_like_dynamic_filter_noise(value, _DYNAMIC_FILTER_MAX_VALUE_LENGTH)


def _flatten_specs(specs):
    flattened = {}

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, dict):
                    walk(value)
                    continue
                if isinstance(value, list):
                    value = ', '.join(str(item) for item in value if item)
                key_text = str(key).strip()
                value_text = str(value or '').strip()
                if not key_text or not value_text:
                    continue
                if key_text not in flattened:
                    flattened[key_text] = value_text

    walk(specs or {})
    return flattened


def _build_dynamic_filter_groups(products, lang):
    key_stats = {}
    for product in products:
        for key, value in getattr(product, 'flat_specs', {}).items():
            if not _is_dynamic_filter_key_allowed(key) or not _is_dynamic_filter_value_allowed(value):
                continue
            normalized_value = _normalize_filter_text(value)
            if not normalized_value:
                continue
            stats = key_stats.setdefault(
                key,
                {'values': {}, 'coverage': 0},
            )
            stats['coverage'] += 1
            stats['values'].setdefault(normalized_value, {'label': value, 'count': 0})
            stats['values'][normalized_value]['count'] += 1

    sorted_keys = sorted(
        key_stats.items(),
        key=lambda item: (item[1]['coverage'], len(item[1]['values'])),
        reverse=True,
    )

    groups = []
    for key, stats in sorted_keys:
        if len(stats['values']) < _DYNAMIC_FILTER_MIN_OPTIONS or len(stats['values']) > _DYNAMIC_FILTER_MAX_OPTIONS:
            continue
        if stats['coverage'] < _DYNAMIC_FILTER_MIN_COVERAGE:
            continue

        group_slug = slugify(key) or f'filter-{len(groups)}'
        options = sorted(
            stats['values'].values(),
            key=lambda item: (-item['count'], item['label'].lower()),
        )
        groups.append(
            {
                'key': key,
                'param': f'sf_{group_slug}',
                'title': key,
                'collapse_id': f'{lang}-sf-{group_slug}',
                'options': [
                    {
                        'value': option['label'],
                        'label': option['label'],
                    }
                    for option in options
                ],
            }
        )

    return groups


def _apply_dynamic_filters(products, groups, selected_values):
    if not groups:
        return products

    filtered = []
    for product in products:
        matches_all = True
        for group in groups:
            selected = selected_values.get(group['param'], [])
            if not selected:
                continue
            product_value = _normalize_filter_text(getattr(product, 'flat_specs', {}).get(group['key']))
            selected_values_normalized = {_normalize_filter_text(value) for value in selected}
            if not product_value or product_value not in selected_values_normalized:
                matches_all = False
                break
        if matches_all:
            filtered.append(product)
    return filtered


def _get_product_slug(product, lang):
    raw_name = getattr(product, f'name_{lang}', '') or getattr(product, 'name', '') or ''
    product_slug = slugify(raw_name, allow_unicode=True).replace('-', '_')
    return product_slug or f'product_{product.id}'


def _build_url_with_query(url, query_params=None):
    if not query_params:
        return url
    query_string = query_params.urlencode()
    if not query_string:
        return url
    return f'{url}?{query_string}'


def _build_language_urls(route_name, route_kwargs=None, query_params=None):
    route_kwargs = route_kwargs or {}
    return {
        language_code: _build_url_with_query(
            reverse(route_name, kwargs={'lang': language_code, **route_kwargs}),
            query_params,
        )
        for language_code in ('ru', 'ua', 'en')
    }


def _build_product_detail_language_urls(category, product, query_params=None):
    urls = {}
    for language_code in ('ru', 'ua', 'en'):
        urls[language_code] = _build_url_with_query(
            reverse(
                'product_detail',
                kwargs={
                    'lang': language_code,
                    'section_id': category.id_name,
                    'product_slug': _get_product_slug(product, language_code),
                },
            ),
            query_params,
        )
    return urls


def _get_section_name(category, lang):
    if lang == 'ru':
        return category.name_ru
    if lang == 'ua':
        return category.name_ua
    return category.name_en


def _get_article_slug(article, lang):
    title = getattr(article, f'title_{lang}', '') or article.title_ru or article.title_ua or article.title_en or article.slug
    localized_slug = slugify(title, allow_unicode=True)
    return localized_slug or article.slug


def _get_article_labels(lang):
    labels = {
        'ru': {
            'articles': 'Статьи',
            'published': 'Опубликовано',
            'back_to_articles': 'Назад к статьям',
            'no_articles': 'Статей пока нет.',
            'read_more': 'Читать далее',
        },
        'ua': {
            'articles': 'Статті',
            'published': 'Опубліковано',
            'back_to_articles': 'Назад до статей',
            'no_articles': 'Статей поки немає.',
            'read_more': 'Читати далі',
        },
        'en': {
            'articles': 'Articles',
            'published': 'Published',
            'back_to_articles': 'Back to articles',
            'no_articles': 'No articles yet.',
            'read_more': 'Read more',
        },
    }
    return labels.get(lang, labels['en'])


def _get_published_articles_queryset():
    now = timezone.now()
    return (
        Article.objects.filter(is_published=True)
        .filter(Q(published_at__isnull=True) | Q(published_at__lte=now))
        .prefetch_related('images')
    )


def _prepare_article(article, lang):
    article.title = getattr(article, f'title_{lang}', '') or article.title_ru or article.title_ua or article.title_en
    article.excerpt = getattr(article, f'excerpt_{lang}', '') or ''
    article.content = getattr(article, f'content_{lang}', '') or ''
    article.detail_slug = _get_article_slug(article, lang)
    article.detail_url = reverse('article_detail', args=[lang, article.id, article.detail_slug])
    article.display_images = list(article.images.all())
    article.primary_image = article.display_images[0] if article.display_images else None
    if article.primary_image:
        article.primary_image_alt = (
            getattr(article.primary_image, f'alt_{lang}', '')
            or article.title
        )
    else:
        article.primary_image_alt = article.title
    return article


def _build_article_detail_language_urls(article):
    return {
        language_code: reverse(
            'article_detail',
            kwargs={
                'lang': language_code,
                'article_id': article.id,
                'article_slug': _get_article_slug(article, language_code),
            },
        )
        for language_code in ('ru', 'ua', 'en')
    }


def _get_product_detail_labels(lang):
    labels = {
        'ru': {
            'products': 'Товары',
            'description': 'Описание',
            'specifications': 'Характеристики',
            'not_specified': 'Характеристики не указаны.',
            'back_to_category': 'Назад к категории',
            'source': 'Источник',
            'other_languages': 'Другие языки',
            'brand': 'Бренд',
            'breakdowns': 'Поломки',
            'possible_causes': 'Возможные причины',
            'what_to_check': 'Что проверить',
            'how_to_fix': 'Как исправить',
            'read_breakdown': 'Открыть страницу ошибки',
            'back_to_product': 'Назад к товару',
        },
        'ua': {
            'products': 'Товари',
            'description': 'Опис',
            'specifications': 'Характеристики',
            'not_specified': 'Характеристики не вказані.',
            'back_to_category': 'Назад до категорії',
            'source': 'Джерело',
            'other_languages': 'Інші мови',
            'brand': 'Бренд',
            'breakdowns': 'Поломки',
            'possible_causes': 'Можливі причини',
            'what_to_check': 'Що перевірити',
            'how_to_fix': 'Як виправити',
            'read_breakdown': 'Відкрити сторінку помилки',
            'back_to_product': 'Назад до товару',
        },
        'en': {
            'products': 'Products',
            'description': 'Description',
            'specifications': 'Specifications',
            'not_specified': 'No specifications available.',
            'back_to_category': 'Back to category',
            'source': 'Source',
            'other_languages': 'Other languages',
            'brand': 'Brand',
            'breakdowns': 'Breakdowns',
            'possible_causes': 'Possible causes',
            'what_to_check': 'What to check',
            'how_to_fix': 'How to fix',
            'read_breakdown': 'Open breakdown page',
            'back_to_product': 'Back to product',
        },
    }
    return labels.get(lang, labels['en'])


def _prepare_breakdowns(raw_breakdowns, labels, lang):
    prepared_breakdowns = []
    suffix = '' if lang == 'ru' else f'_{lang}'

    for breakdown in raw_breakdowns:
        sections = []
        for field_name, label_key in (
            ('possible_causes', 'possible_causes'),
            ('what_to_check', 'what_to_check'),
            ('how_to_fix', 'how_to_fix'),
        ):
            content = (getattr(breakdown, f'{field_name}{suffix}', '') or '').strip()
            if not content:
                continue
            sections.append({
                'label': labels[label_key],
                'content': content,
            })

        if sections:
            title = (getattr(breakdown, f'title{suffix}', '') or '').strip()
            breakdown.display_title = title or breakdown.title
            breakdown.display_sections = sections
            prepared_breakdowns.append(breakdown)

    return prepared_breakdowns


def _prepare_product(product, lang):
    product.name = getattr(product, f'name_{lang}')
    product.description = getattr(product, f'description_{lang}')
    product.specs = _get_specs_for_language(product, lang)
    product.flat_specs = _flatten_specs(product.specs)
    product.brand_name = _extract_brand(product, lang)
    product.brand_slug = get_brand_slug(product.brand_name)
    product.detail_slug = _get_product_slug(product, lang)
    product.detail_url = reverse('product_detail', args=[lang, product.category.id_name, product.detail_slug])
    return product


def _get_breakdown_slug(breakdown, lang):
    suffix = '' if lang == 'ru' else f'_{lang}'
    candidates = [
        getattr(breakdown, f'title{suffix}', ''),
        breakdown.title,
        getattr(breakdown, f'description{suffix}', ''),
        breakdown.description,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        matches = _ERROR_CODE_PATTERN.finditer(candidate)
        code_slugs = []
        for match in matches:
            code = match.group(1).replace(' ', '').replace('-', '_')
            code_slug = slugify(code, allow_unicode=False).replace('-', '_')
            if code_slug and code_slug not in code_slugs:
                code_slugs.append(code_slug)
        if not code_slugs:
            continue
        return '_'.join(code_slugs)

    title = getattr(breakdown, f'title{suffix}', '') or breakdown.title or f'breakdown-{breakdown.id}'
    slug = slugify(title, allow_unicode=True).replace('-', '_')
    return slug or f'breakdown_{breakdown.id}'


def _build_breakdown_detail_language_urls(category, product, breakdown, query_params=None):
    return {
        language_code: _build_url_with_query(
            reverse(
                'breakdown_detail',
                kwargs={
                    'lang': language_code,
                    'section_id': category.id_name,
                    'product_slug': _get_product_slug(product, language_code),
                    'breakdown_slug': _get_breakdown_slug(breakdown, language_code),
                },
            ),
            query_params,
        )
        for language_code in ('ru', 'ua', 'en')
    }

def index(request, lang='ru'):
    categories = list(
        Category.objects.annotate(product_count=Count('products'))
        .order_by('-product_count', 'id')
    )
    articles = [
        _prepare_article(article, lang)
        for article in _get_published_articles_queryset()[:3]
    ]
    context = {
        'categories': categories[:6],
        'featured_articles': articles,
        'metrics': {
            'products': Product.objects.count(),
            'breakdowns': Breakdown.objects.count(),
            'categories': len(categories),
        },
        'language_urls': _build_language_urls('index_lang'),
        'lang': lang,
        'page_mode': 'home',
    }
    template_path = 'catalog/home.html'
    return render(request, template_path, context)

def products_index(request, lang='ru'):
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count', 'id')
    context = {
        'categories': categories,
        'featured_articles': [],
        'metrics': None,
        'language_urls': _build_language_urls('products_index'),
        'lang': lang,
        'page_mode': 'catalog',
    }
    template_path = 'catalog/home.html'
    return render(request, template_path, context)

def section_view(request, section_id, lang='ru'):
    category = get_object_or_404(Category, id_name=section_id)
    products_list = [
        _prepare_product(product, lang)
        for product in Product.objects.select_related('brand', 'category').filter(category=category)
    ]
    products_list.sort(key=lambda product: (product.brand_name.lower(), (product.name or '').lower(), product.id))

    vacuum_filter_groups = []
    selected_filter_state = {}
    filtered_products = products_list

    if category.id_name in {'cleaners', 'coffeemachines', 'cookers', 'dishwashers', 'fridges', 'hobs', 'ovens', 'wash', 'washers', 'microwaves'}:
        vacuum_filter_groups = get_section_filter_groups(category.id_name, lang)
        selected_filter_state = build_filter_state(vacuum_filter_groups, request.GET)
        filtered_products = apply_section_filters(
            products_list,
            category.id_name,
            lang,
            vacuum_filter_groups,
            selected_filter_state,
        )
        vacuum_filter_groups = enrich_filter_groups(vacuum_filter_groups, selected_filter_state)

    brand_map = {}
    for product in filtered_products:
        brand_data = brand_map.setdefault(product.brand_slug, {
            'name': product.brand_name,
            'slug': product.brand_slug,
            'count': 0,
        })
        brand_data['count'] += 1

    brands = list(brand_map.values())
    selected_brands = request.GET.getlist('brand')
    if selected_brands:
        filtered_products = [
            product for product in filtered_products
            if product.brand_slug in selected_brands
        ]
    brands = build_brand_choices(brands, selected_brands)

    paginator = Paginator(filtered_products, 12)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    brand_groups_map = {}
    for product in products.object_list:
        brand_groups_map.setdefault(product.brand_name, []).append(product)
    brand_groups = [
        {'name': brand_name, 'products': items}
        for brand_name, items in brand_groups_map.items()
    ]

    context = {
        'category': category,
        'products': products,
        'products_count': paginator.count,
        'brand_groups': brand_groups,
        'brands': brands,
        'selected_brands': selected_brands,
        'vacuum_filter_groups': vacuum_filter_groups,
        'filter_labels': get_filter_labels(lang),
        'query_string_without_page': get_query_string_without_page(request.GET),
        'language_urls': _build_language_urls(
            'product_section',
            {'section_id': category.id_name},
            request.GET,
        ),
        'lang': lang,
        'section_name': _get_section_name(category, lang),
    }
    template_path = 'catalog/section_page.html'
    return render(request, template_path, context)


def product_detail_view(request, lang, section_id, product_slug):
    category = get_object_or_404(Category, id_name=section_id)
    selected_product = None
    labels = _get_product_detail_labels(lang)

    for product in Product.objects.select_related('brand', 'category', 'breakdown_group').prefetch_related('breakdown_groups').filter(category=category).order_by('id'):
        if _get_product_slug(product, lang) != product_slug:
            continue
        selected_product = _prepare_product(product, lang)
        break

    if selected_product is None:
        raise Http404('Product not found')

    breakdowns = []
    breakdown_group_ids = set()
    if selected_product.breakdown_group_id:
        breakdown_group_ids.add(selected_product.breakdown_group_id)
    breakdown_group_ids.update(selected_product.breakdown_groups.values_list('id', flat=True))
    if selected_product.brand_id:
        breakdown_group_ids.update(
            selected_product.category.breakdown_groups.filter(
                Q(brand_id=selected_product.brand_id) | Q(brand__isnull=True)
            ).values_list('id', flat=True)
        )
    else:
        breakdown_group_ids.update(
            selected_product.category.breakdown_groups.filter(brand__isnull=True).values_list('id', flat=True)
        )

    if breakdown_group_ids:
        breakdowns = _prepare_breakdowns(
            Breakdown.objects.filter(breakdown_group_id__in=breakdown_group_ids).order_by('breakdown_group__name', 'title'),
            labels,
            lang,
        )
        for breakdown in breakdowns:
            breakdown.detail_slug = _get_breakdown_slug(breakdown, lang)
            breakdown.detail_url = reverse(
                'breakdown_detail',
                kwargs={
                    'lang': lang,
                    'section_id': category.id_name,
                    'product_slug': selected_product.detail_slug,
                    'breakdown_slug': breakdown.detail_slug,
                },
            )

    context = {
        'base_template': 'catalog/site_base.html',
        'category': category,
        'section_name': _get_section_name(category, lang),
        'product': selected_product,
        'breakdowns': breakdowns,
        'language_urls': _build_product_detail_language_urls(category, selected_product, request.GET),
        'labels': labels,
        'lang': lang,
    }
    return render(request, 'catalog/product_detail.html', context)


def breakdown_detail_view(request, lang, section_id, product_slug, breakdown_slug):
    category = get_object_or_404(Category, id_name=section_id)
    selected_product = None
    labels = _get_product_detail_labels(lang)

    for product in Product.objects.select_related('brand', 'category', 'breakdown_group').prefetch_related('breakdown_groups').filter(category=category).order_by('id'):
        if _get_product_slug(product, lang) != product_slug:
            continue
        selected_product = _prepare_product(product, lang)
        break

    if selected_product is None:
        raise Http404('Product not found')

    breakdown_group_ids = set()
    if selected_product.breakdown_group_id:
        breakdown_group_ids.add(selected_product.breakdown_group_id)
    breakdown_group_ids.update(selected_product.breakdown_groups.values_list('id', flat=True))
    if selected_product.brand_id:
        breakdown_group_ids.update(
            selected_product.category.breakdown_groups.filter(
                Q(brand_id=selected_product.brand_id) | Q(brand__isnull=True)
            ).values_list('id', flat=True)
        )
    else:
        breakdown_group_ids.update(
            selected_product.category.breakdown_groups.filter(brand__isnull=True).values_list('id', flat=True)
        )

    if not breakdown_group_ids:
        raise Http404('Breakdown not found')

    breakdowns = _prepare_breakdowns(
        Breakdown.objects.filter(breakdown_group_id__in=breakdown_group_ids).order_by('breakdown_group__name', 'title'),
        labels,
        lang,
    )
    for item in breakdowns:
        item.detail_slug = _get_breakdown_slug(item, lang)
        item.detail_url = reverse(
            'breakdown_detail',
            kwargs={
                'lang': lang,
                'section_id': category.id_name,
                'product_slug': selected_product.detail_slug,
                'breakdown_slug': item.detail_slug,
            },
        )

    requested_breakdown_slug = slugify(breakdown_slug, allow_unicode=True).replace('-', '_')
    breakdown = next((item for item in breakdowns if item.detail_slug == requested_breakdown_slug), None)
    if breakdown is None:
        raise Http404('Breakdown not found')

    context = {
        'base_template': 'catalog/site_base.html',
        'category': category,
        'section_name': _get_section_name(category, lang),
        'product': selected_product,
        'breakdown': breakdown,
        'related_breakdowns': [item for item in breakdowns if item.id != breakdown.id][:6],
        'language_urls': _build_breakdown_detail_language_urls(category, selected_product, breakdown, request.GET),
        'labels': labels,
        'lang': lang,
    }
    return render(request, 'catalog/breakdown_detail.html', context)

def search_view(request, lang='ru'):
    query = request.GET.get('q', '')
    products_list = Product.objects.none()
    
    if query:
        products_list = Product.objects.select_related('brand', 'category').filter(
             Q(**{f'name_{lang}__icontains': query}) |
             Q(product_folder__icontains=query)
         ).order_by('id')
    
    paginator = Paginator(products_list, 12)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    for product in products:
        _prepare_product(product, lang)

    context = {
        'products': products,
        'products_count': products.paginator.count,
        'query': query,
        'language_urls': _build_language_urls('search', query_params=request.GET),
        'lang': lang,
    }
    template_path = 'catalog/search_results.html'
    return render(request, template_path, context)


def articles_index(request, lang='ru'):
    articles_qs = _get_published_articles_queryset()
    paginator = Paginator(articles_qs, 9)
    page_number = request.GET.get('page')
    articles_page = paginator.get_page(page_number)
    articles = [_prepare_article(article, lang) for article in articles_page.object_list]
    articles_page.object_list = articles

    context = {
        'articles': articles_page,
        'labels': _get_article_labels(lang),
        'language_urls': _build_language_urls('articles_index'),
        'base_template': 'catalog/site_base.html',
        'lang': lang,
    }
    return render(request, 'catalog/articles_index.html', context)


def article_detail_view(request, lang, article_id, article_slug):
    article = get_object_or_404(
        _get_published_articles_queryset(),
        id=article_id,
    )

    article = _prepare_article(article, lang)
    if article.detail_slug != article_slug:
        raise Http404('Article not found')

    context = {
        'article': article,
        'labels': _get_article_labels(lang),
        'language_urls': _build_article_detail_language_urls(article),
        'base_template': 'catalog/site_base.html',
        'lang': lang,
    }
    return render(request, 'catalog/article_detail.html', context)
