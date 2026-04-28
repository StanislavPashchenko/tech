import os
import json
from django.conf import settings

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
                except Exception as e:
                    print(f"Error reading {json_path}: {e}")
                    
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
