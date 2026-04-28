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


def seed_vacuum_brands(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    Product = apps.get_model('catalog', 'Product')
    VacuumBrand = apps.get_model('catalog', 'VacuumBrand')

    brand_names = load_brand_names()
    brand_objects = {}

    for brand_name in brand_names:
        brand, _ = VacuumBrand.objects.get_or_create(
            name=brand_name,
            defaults={'slug': slugify(brand_name) or 'no-brand'},
        )
        brand_objects[brand_name] = brand

    brand_lookup = {normalize_brand_key(brand_name): brand_name for brand_name in brand_names}
    ordered_keys = sorted(brand_lookup.keys(), key=len, reverse=True)

    cleaners_category = Category.objects.filter(id_name='cleaners').first()
    if cleaners_category is None:
        return

    for product in Product.objects.filter(category=cleaners_category):
        brand_name = find_brand_name(
            product.product_folder,
            [product.name_ru, product.name_ua, product.name_en],
            brand_lookup,
            ordered_keys,
        )
        if brand_name:
            product.brand = brand_objects[brand_name]
            product.save(update_fields=['brand'])


def unseed_vacuum_brands(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    VacuumBrand = apps.get_model('catalog', 'VacuumBrand')

    Product.objects.update(brand=None)
    VacuumBrand.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_vacuumbrand_product_brand'),
    ]

    operations = [
        migrations.RunPython(seed_vacuum_brands, unseed_vacuum_brands),
    ]
