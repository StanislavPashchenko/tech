import os
import re

from django.conf import settings
from django.db import migrations
from django.utils.text import slugify


def normalize_brand_key(value):
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def load_brand_names():
    file_path = os.path.join(settings.BASE_DIR, 'brands.txt')
    with open(file_path, 'r', encoding='utf-8') as file:
        return [
            line.replace('☐', '', 1).strip()
            for line in file.readlines()
            if line.strip().startswith('☐')
        ]


def find_brand_name(product_folder, names, brand_lookup, ordered_keys):
    candidates = []
    if product_folder:
        candidates.append(product_folder)
    candidates.extend(name for name in names if name)

    for candidate in candidates:
        normalized_candidate = normalize_brand_key(
            str(candidate).lower().replace('-', ' ').replace('_', ' ')
        )
        for brand_key in ordered_keys:
            if normalized_candidate.startswith(brand_key):
                return brand_lookup[brand_key]
    return None


def sync_vacuum_brands(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    Product = apps.get_model('catalog', 'Product')
    VacuumBrand = apps.get_model('catalog', 'VacuumBrand')

    brand_names = load_brand_names()
    desired_name_by_key = {normalize_brand_key(brand_name): brand_name for brand_name in brand_names}
    ordered_keys = sorted(desired_name_by_key.keys(), key=len, reverse=True)

    existing_brands = list(VacuumBrand.objects.all().order_by('id'))
    existing_by_name = {brand.name: brand for brand in existing_brands}
    existing_by_key = {}
    for brand in existing_brands:
        existing_by_key.setdefault(normalize_brand_key(brand.name), []).append(brand)

    used_brand_ids = set()
    desired_brands = {}

    for brand_name in brand_names:
        brand = existing_by_name.get(brand_name)
        if brand and brand.id in used_brand_ids:
            brand = None

        if brand is None:
            for candidate in existing_by_key.get(normalize_brand_key(brand_name), []):
                if candidate.id not in used_brand_ids:
                    brand = candidate
                    break

        desired_slug = slugify(brand_name) or 'no-brand'

        if brand is None:
            brand = VacuumBrand.objects.create(name=brand_name, slug=desired_slug)
        else:
            update_fields = []
            if brand.name != brand_name:
                brand.name = brand_name
                update_fields.append('name')
            if brand.slug != desired_slug:
                brand.slug = desired_slug
                update_fields.append('slug')
            if update_fields:
                brand.save(update_fields=update_fields)

        used_brand_ids.add(brand.id)
        desired_brands[brand_name] = brand

    desired_brand_ids = {brand.id for brand in desired_brands.values()}
    replacement_by_stale_id = {}

    for brand in existing_brands:
        if brand.id in desired_brand_ids:
            continue
        replacement_name = desired_name_by_key.get(normalize_brand_key(brand.name))
        if replacement_name:
            replacement_by_stale_id[brand.id] = desired_brands[replacement_name]

    cleaners_category = Category.objects.filter(id_name='cleaners').first()
    if cleaners_category is not None:
        for product in Product.objects.filter(category=cleaners_category).select_related('brand'):
            desired_brand_name = find_brand_name(
                product.product_folder,
                [product.name_ru, product.name_ua, product.name_en],
                desired_name_by_key,
                ordered_keys,
            )
            replacement_brand = desired_brands.get(desired_brand_name) if desired_brand_name else None
            direct_replacement = replacement_by_stale_id.get(product.brand_id)

            if replacement_brand and product.brand_id != replacement_brand.id:
                product.brand = replacement_brand
                product.save(update_fields=['brand'])
                continue

            if direct_replacement and product.brand_id != direct_replacement.id:
                product.brand = direct_replacement
                product.save(update_fields=['brand'])

    stale_brand_ids = [brand.id for brand in existing_brands if brand.id not in desired_brand_ids]
    if stale_brand_ids:
        Product.objects.filter(brand_id__in=stale_brand_ids).update(brand=None)
        VacuumBrand.objects.filter(id__in=stale_brand_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0003_seed_vacuum_brands'),
    ]

    operations = [
        migrations.RunPython(sync_vacuum_brands, migrations.RunPython.noop),
    ]
