import os
import json
import re
import logging
from copy import deepcopy
from django.conf import settings

logger = logging.getLogger(__name__)

def get_products(section_folder, lang='ru'):
    """
    section_folder: name of the folder starting with last_ (e.g. 'last_CoffeeMachines')
    lang: 'ru', 'ua', or 'en'
    """
    base_dir = settings.BASE_DIR
    folder_path = os.path.join(base_dir, section_folder)
    products = []
    
    if not os.path.exists(folder_path):
        return []
        
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            json_file = f"new_{lang}.json"
            json_path = os.path.join(item_path, json_file)
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        products.append(data)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    logger.exception("Error reading product JSON: %s", json_path)
                    
    return products

def get_sections():
    sections = [
        {'id': 'dishwashers', 'folder': '1/last_Dishwashers', 'name': {'ru': 'Посудомоечные машины', 'ua': 'Посудомийні машини', 'en': 'Dishwashers'}},
        {'id': 'vacuum_cleaners', 'folder': 'last_cleaners', 'name': {'ru': 'Пылесосы', 'ua': 'Пилососи', 'en': 'Vacuum Cleaners'}},
        {'id': 'hobs', 'folder': '1/last_Hobs', 'name': {'ru': 'Варочные поверхности', 'ua': 'Варильні поверхні', 'en': 'Hobs'}},
        {'id': 'ovens', 'folder': '1/last_Ovens', 'name': {'ru': 'Духовые шкафы', 'ua': 'Духові шафи', 'en': 'Ovens'}},
        {'id': 'washers', 'folder': '1/last_wash', 'name': {'ru': 'Стиральные машины', 'ua': 'Пральні машини', 'en': 'Washing Machines'}},
        {'id': 'coffee_machines', 'folder': '1/last_CoffeeMachines', 'name': {'ru': 'Кофемашины', 'ua': 'Кавомашини', 'en': 'Coffee Machines'}},
        {'id': 'cookers', 'folder': '1/last_cookers', 'name': {'ru': 'Плиты', 'ua': 'Плити', 'en': 'Cookers'}},
        {'id': 'fridges', 'folder': '1/last_fridges', 'name': {'ru': 'Холодильники', 'ua': 'Холодильники', 'en': 'Refrigerators'}},
        {'id': 'microwaves', 'folder': '1/last_Microwaves', 'name': {'ru': 'Микроволновые печи', 'ua': 'Мікрохвильові печі', 'en': 'Microwaves'}},
    ]
    return sections


_DRYER_FIELD_CANDIDATES = {
    'ru': {
        'dryer': ['Сушилка', 'Сушка'],
        'drying_capacity': ['Загрузка для сушки', 'Загрузка для сушилки'],
    },
    'ua': {
        'dryer': ['Сушарка', 'Сушка'],
        'drying_capacity': ['Завантаження для сушіння', 'Завантаження для сушки'],
    },
    'en': {
        'dryer': ['Dryer'],
        'drying_capacity': ['Drying capacity'],
    },
}

_TRUTHY_VALUES = {
    'ru': {'да', 'есть', 'true', 'yes', '1', '+'},
    'ua': {'так', 'є', 'true', 'yes', '1', '+'},
    'en': {'yes', 'true', '1', '+'},
}

_FALSY_VALUES = {
    'ru': {'нет', 'false', 'no', '0', '-'},
    'ua': {'ні', 'нет', 'false', 'no', '0', '-'},
    'en': {'no', 'false', '0', '-'},
}

_NO_VALUE_BY_LANG = {
    'ru': 'нет',
    'ua': 'ні',
    'en': 'no',
}


def extract_drying_flag_from_html(html):
    if not html:
        return False
    if re.search(r'class\s*=\s*[\'"][^\'"]*\bprop-y\b', html, flags=re.IGNORECASE):
        return True
    if re.search(r'class\s*=\s*[\'"][^\'"]*\bprop-n\b', html, flags=re.IGNORECASE):
        return False
    return False


def _first_existing_key(mapping, candidates):
    for key in candidates:
        if key in mapping:
            return key
    return None


def _normalize_flag(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value).strip().lower()


def _is_truthy_flag(value, lang):
    normalized = _normalize_flag(value)
    if not normalized:
        return False
    truthy = _TRUTHY_VALUES.get(lang, _TRUTHY_VALUES['en'])
    falsy = _FALSY_VALUES.get(lang, _FALSY_VALUES['en'])
    if normalized in falsy:
        return False
    if normalized in truthy:
        return True
    return normalized not in {'', '0', 'false', 'no'}


def specs_need_page_check(specs, lang):
    if not isinstance(specs, dict):
        return False
    general = specs.get('general')
    if not isinstance(general, dict):
        return False

    fields = _DRYER_FIELD_CANDIDATES.get(lang, _DRYER_FIELD_CANDIDATES['en'])
    dryer_key = _first_existing_key(general, fields['dryer'])
    if not dryer_key:
        return False
    if not _is_truthy_flag(general.get(dryer_key), lang):
        return False

    drying_capacity_key = _first_existing_key(general, fields['drying_capacity'])
    return not (drying_capacity_key and str(general.get(drying_capacity_key) or '').strip())


def update_drying_fields(specs, lang):
    if not isinstance(specs, dict):
        return specs

    fixed = deepcopy(specs)
    general = fixed.get('general')
    if not isinstance(general, dict):
        return fixed

    fields = _DRYER_FIELD_CANDIDATES.get(lang, _DRYER_FIELD_CANDIDATES['en'])
    dryer_key = _first_existing_key(general, fields['dryer'])
    if not dryer_key:
        return fixed
    if not _is_truthy_flag(general.get(dryer_key), lang):
        return fixed

    general[dryer_key] = _NO_VALUE_BY_LANG.get(lang, _NO_VALUE_BY_LANG['en'])
    drying_capacity_key = _first_existing_key(general, fields['drying_capacity'])
    if drying_capacity_key:
        general.pop(drying_capacity_key, None)

    return fixed


def repair_payload(payload, lang):
    if not isinstance(payload, dict):
        return payload

    fixed = deepcopy(payload)
    for key in ('detailed_specs', 'raw_specs'):
        if isinstance(fixed.get(key), dict):
            fixed[key] = update_drying_fields(fixed[key], lang)
    return fixed
