from collections import defaultdict

from .models import Product

DEFAULT_DUPLICATE_FIELDS = ('name_ru', 'name_ua', 'name_en')


def collect_product_duplicates(queryset=None, fields=None):
    fields = tuple(fields or DEFAULT_DUPLICATE_FIELDS)
    if queryset is None:
        queryset = Product.objects.all()
    rows = list(
        queryset.select_related('category', 'brand').values(
            'id',
            'category__name_ru',
            'brand__name',
            *fields,
        )
    )

    result = {}
    for field in fields:
        groups = defaultdict(list)
        for row in rows:
            value = row.get(field)
            if value is None:
                continue
            value = value.strip()
            if not value:
                continue
            groups[value].append({
                'id': row['id'],
                'category': row['category__name_ru'],
                'brand': row['brand__name'],
            })

        duplicates = [
            {'value': value, 'items': items}
            for value, items in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))
            if len(items) > 1
        ]
        result[field] = duplicates

    return result


def count_duplicate_groups(duplicates_by_field):
    return sum(len(groups) for groups in duplicates_by_field.values())


def count_duplicate_rows(duplicates_by_field):
    return sum(
        len(group['items'])
        for groups in duplicates_by_field.values()
        for group in groups
    )
