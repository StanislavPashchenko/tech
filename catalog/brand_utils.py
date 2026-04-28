import os
import re
from functools import lru_cache

from django.conf import settings
from django.utils.text import slugify

BRAND_NAME_ALIASES = {
    'evolvo': 'Evolveo',
    'evolveo': 'Evolveo',
    'firstaustria': 'FIRST Austria',
    'frsaustria': 'FIRST Austria',
    'hoto': 'HOTO',
    'ibot': 'iBot',
    'iboto': 'iBoto',
    'icebo': 'iClebo',
    'iclebo': 'iClebo',
    'idrobasa': 'Idrobase',
    'idrobase': 'Idrobase',
    'raycop': 'RAYCOP',
    'settiplus': 'SettiPlus',
    'xclea': 'XCLEA',
}


def normalize_brand_key(value):
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def format_fallback_brand(value):
    if not value:
        return ''
    if value.isupper():
        return value
    if len(value) <= 3:
        return value.upper()
    return value.capitalize()


@lru_cache(maxsize=1)
def load_vacuum_brand_names():
    file_path = os.path.join(settings.BASE_DIR, 'brands.txt')
    with open(file_path, 'r', encoding='utf-8') as file:
        brand_names = [
            line.replace('☐', '', 1).strip()
            for line in file.readlines()
            if line.strip().startswith('☐')
        ]
    return tuple(brand_names)


@lru_cache(maxsize=1)
def load_vacuum_brand_lookup():
    brands = load_vacuum_brand_names()
    by_key = {normalize_brand_key(brand): brand for brand in brands}
    by_key.update({
        normalize_brand_key(alias): canonical_name
        for alias, canonical_name in BRAND_NAME_ALIASES.items()
    })
    ordered_keys = sorted(by_key.keys(), key=len, reverse=True)
    return by_key, ordered_keys


def _extract_fallback_brand(source):
    tokens = [
        re.sub(r"(^[^0-9A-Za-zА-Яа-яІіЇїЄєЁё']+|[^0-9A-Za-zА-Яа-яІіЇїЄєЁё&+.'-]+$)", '', token)
        for token in re.split(r'[_\-\s]+', str(source or '').strip())
    ]
    tokens = [token for token in tokens if token]
    if not tokens:
        return ''

    candidate = tokens[0]
    normalized_candidate = normalize_brand_key(candidate)
    if normalized_candidate in BRAND_NAME_ALIASES:
        return BRAND_NAME_ALIASES[normalized_candidate]

    if any('A' <= char <= 'Z' or 'А' <= char <= 'Я' or char in 'ІЇЄЁ' for char in candidate):
        return candidate
    return format_fallback_brand(candidate)


def find_vacuum_brand_name(product_folder='', names=None):
    by_key, ordered_keys = load_vacuum_brand_lookup()
    candidates = []
    if product_folder:
        candidates.append(str(product_folder))
    if names:
        candidates.extend(name for name in names if name)

    normalized_candidates = []
    for candidate in candidates:
        lowered = str(candidate).lower().replace('-', ' ').replace('_', ' ')
        normalized_candidates.append(normalize_brand_key(lowered))

    for candidate in normalized_candidates:
        if not candidate:
            continue
        for brand_key in ordered_keys:
            if candidate.startswith(brand_key):
                return by_key[brand_key]

    for value in names or []:
        brand_name = _extract_fallback_brand(value)
        if brand_name:
            return brand_name

    if product_folder:
        brand_name = _extract_fallback_brand(product_folder)
        if brand_name:
            return brand_name

    return ''


def get_brand_slug(brand_name):
    return slugify(brand_name) or 'no-brand'
