from copy import deepcopy
from functools import lru_cache
import os
import re

from django.conf import settings
from django.utils.text import slugify

VACUUM_FILTER_KEYS = [
    'vacuum_type',
    'floor_washing',
    'cleaning',
    'power_source',
    'dust_collector',
    'motor_power',
    'suction_power_w',
    'suction_force_pa',
    'features',
    'nozzles',
    'robot_features',
    'extra',
    'noise_level',
    'battery',
    'battery_type',
    'runtime',
    'dust_capacity',
    'water_tank',
    'cable_length',
    'robot_height',
    'robot_shape',
    'weight',
]

COFFEE_FILTER_KEYS = [
    'coffee_type',
    'used_coffee',
    'coffee_programs',
    'milk_drinks',
    'coffee_adjustments',
    'coffee_features',
    'compatible_capsules',
    'servings_per_cycle',
    'coffee_pressure',
    'coffee_power',
    'coffee_water_tank',
    'grinder_capacity',
]

COOKER_FILTER_KEYS = [
    'cooker_type',
    'burner_type',
    'burners_count',
    'hob_surface',
    'cooker_design',
    'small_burner_power',
    'big_burner_power',
    'oven_type',
    'oven_capacity',
    'oven_power',
    'cooker_features',
    'oven_features',
    'release_year',
    'oven_cleaning',
    'burner_controls',
    'combined_burners',
    'energy_class',
    'connected_load',
    'cooker_width',
    'cooker_depth',
    'burner_grates',
    'cooker_lid',
    'country_of_origin',
]

DISHWASHER_FILTER_KEYS = [
    'dishwasher_format',
    'dishwasher_width',
    'dishwasher_place_settings',
    'dishwasher_programs',
    'dishwasher_features',
    'dishwasher_dryer_type',
    'dishwasher_water_consumption',
    'dishwasher_energy_class',
    'dishwasher_noise_level',
    'dishwasher_controls',
    'dishwasher_country_of_origin',
    'dishwasher_release_year',
]

FRIDGE_FILTER_KEYS = [
    'fridge_type',
    'fridge_chambers',
    'fridge_freezer_position',
    'fridge_features',
    'fridge_compartments',
    'fridge_additional',
    'fridge_height',
    'fridge_width',
    'fridge_energy_class',
    'fridge_release_year',
    'fridge_climate_class',
    'fridge_controls',
    'fridge_capacity',
    'fridge_shelves',
    'freezer_capacity',
    'freezer_drawers',
    'fridge_autonomy_time',
    'fridge_noise_level',
    'fridge_depth',
    'fridge_country_of_origin',
]

HOB_FILTER_KEYS = [
    'hob_device',
    'hob_burner_type',
    'hob_burners_count',
    'hob_surface',
    'hob_design',
    'hob_controls',
    'hob_features',
    'hob_extra',
    'hob_release_year',
    'hob_includes_burners',
    'hob_combined_burners',
    'hob_small_burner_power',
    'hob_big_burner_power',
    'hob_connected_load',
    'hob_width',
    'hob_depth',
    'hob_cutout_width',
    'hob_cutout_depth',
    'hob_frame',
    'hob_burner_grates',
    'hob_country_of_origin',
]

OVEN_FILTER_KEYS = [
    'oven_device_type',
    'oven_capacity_filter',
    'oven_cooking_modes',
    'oven_modes_count',
    'oven_min_temperature',
    'oven_max_temperature',
    'oven_features_list',
    'oven_cleaning_type',
    'oven_switches',
    'oven_guides_filter',
    'oven_energy_class_filter',
    'oven_connected_load_filter',
    'oven_height_filter',
    'oven_width_filter',
    'oven_cutout_depth',
    'oven_country_of_origin_filter',
]

WASH_FILTER_KEYS = [
    'wash_type',
    'wash_capacity',
    'wash_drying_capacity',
    'wash_spin_speed',
    'wash_features',
    'wash_programmes',
    'wash_controls',
    'wash_protection',
    'wash_depth',
    'wash_release_year',
    'wash_width',
    'wash_height',
    'wash_energy_class',
    'wash_spin_class',
    'wash_noise_level',
    'wash_water_consumption',
    'wash_door_opening',
    'wash_country_of_origin',
]

MICROWAVE_FILTER_KEYS = [
    'microwave_capacity',
    'microwave_power',
    'microwave_features',
    'microwave_extra',
    'microwave_controls',
    'microwave_inner_coating',
    'microwave_door',
    'microwave_door_opening',
    'microwave_release_year',
    'microwave_turntable_diameter',
    'microwave_height',
    'microwave_width',
    'microwave_depth',
]

LANGUAGE_MARKERS = {
    'ru': 'Русский язык:',
    'ua': 'Украинский язык:',
    'en': 'Английский язык:',
}

CATEGORY_FILTER_CONFIGS = {
    'cleaners': {
        'file_name': 'VacuumCleanersFilter.txt',
        'keys': VACUUM_FILTER_KEYS,
        'param_prefix': 'vf',
    },
    'coffeemachines': {
        'file_name': 'CoffeeMachines.txt',
        'keys': COFFEE_FILTER_KEYS,
        'param_prefix': 'cf',
    },
    'cookers': {
        'file_name': 'CookersFilter.txt',
        'keys': COOKER_FILTER_KEYS,
        'param_prefix': 'kf',
    },
    'dishwashers': {
        'file_name': 'Dishwashers.txt',
        'keys': DISHWASHER_FILTER_KEYS,
        'param_prefix': 'df',
    },
    'fridges': {
        'file_name': 'Fridges.txt',
        'keys': FRIDGE_FILTER_KEYS,
        'param_prefix': 'rf',
    },
    'hobs': {
        'file_name': 'Hobs.txt',
        'keys': HOB_FILTER_KEYS,
        'param_prefix': 'hf',
    },
    'ovens': {
        'file_name': 'Ovens.txt',
        'keys': OVEN_FILTER_KEYS,
        'param_prefix': 'of',
    },
    'wash': {
        'file_name': 'WashingMachines.txt',
        'keys': WASH_FILTER_KEYS,
        'param_prefix': 'wf',
    },
    'washers': {
        'file_name': 'WashingMachines.txt',
        'keys': WASH_FILTER_KEYS,
        'param_prefix': 'wf',
    },
    'microwaves': {
        'file_name': 'Microwaves.txt',
        'keys': MICROWAVE_FILTER_KEYS,
        'param_prefix': 'mf',
    },
}

GENERAL_KEYS = {
    'type': {
        'ru': ['Тип'],
        'ua': ['Тип'],
        'en': ['Type'],
    },
    'cleaning': {
        'ru': ['Уборка'],
        'ua': ['Прибирання'],
        'en': ['Cleaning type'],
    },
    'power_source': {
        'ru': ['Источник питания'],
        'ua': ['Джерело живлення'],
        'en': ['Source of power'],
    },
    'dust_collector': {
        'ru': ['Пылесборник'],
        'ua': ['Пилозбірник'],
        'en': ['Dust collector'],
    },
    'motor_power': {
        'ru': ['Потребляемая мощность'],
        'ua': ['Споживана потужність'],
        'en': ['Motor power'],
    },
    'suction_power_w': {
        'ru': ['Мощность всасывания'],
        'ua': ['Потужність всмоктування'],
        'en': ['Suction power'],
    },
    'suction_force_pa': {
        'ru': ['Сила всасывания'],
        'ua': ['Сила всмоктування'],
        'en': ['Suction force'],
    },
    'noise_level': {
        'ru': ['Уровень шума'],
        'ua': ['Рівень шуму'],
        'en': ['Noise level'],
    },
    'battery_type': {
        'ru': ['Тип аккумулятора'],
        'ua': ['Тип акумулятора'],
        'en': ['Battery type'],
    },
    'runtime': {
        'ru': ['Время работы'],
        'ua': ['Час роботи'],
        'en': ['Battery run time', 'Run time'],
    },
    'dust_capacity': {
        'ru': ['Объем пылесборника'],
        'ua': ['Об’єм пилозбірника', "Об'єм пилозбірника"],
        'en': ['Dust collector capacity'],
    },
    'water_tank': {
        'ru': ['Объем емкости для воды'],
        'ua': ['Об’єм ємності для води', "Об'єм ємності для води"],
        'en': ['Water tank capacity'],
    },
    'cable_length': {
        'ru': ['Длина кабеля', 'Длина сетевого шнура'],
        'ua': ['Довжина кабелю', 'Довжина мережевого шнура'],
        'en': ['Cord length', 'Power cord length'],
    },
    'dimensions': {
        'ru': ['Габариты (ВхШхГ)'],
        'ua': ['Габарити (ВхШхГ)'],
        'en': ['Dimensions (HxWxD)'],
    },
    'weight': {
        'ru': ['Вес'],
        'ua': ['Вага'],
        'en': ['Weight'],
    },
    'nozzles': {
        'ru': ['Функции насадок'],
        'ua': ['Функції насадок'],
        'en': ['Nozzle functions'],
    },
    'robot_features': {
        'ru': [
            'Функции робота',
            'Построение карты помещения',
            'Ограничение площади уборки',
            'Память нескольких карт (этажей)',
            'Преодоление порога',
            'Камера видеонаблюдения',
        ],
        'ua': [
            'Функції робота',
            'Побудова карти приміщення',
            'Обмеження площі прибирання',
            'Пам’ять кількох карт (поверхів)',
            "Пам'ять кількох карт (поверхів)",
            'Подолання порога',
            'Камера відеоспостереження',
        ],
        'en': [
            'Robot functions',
            'Room mapping',
            'Cleaning area limitation',
            'Multiple maps memory',
            'Crossing threshold',
            'Security camera',
        ],
    },
    'used_coffee': {
        'ru': ['Используемый кофе'],
        'ua': ['Кава', 'Використовувана кава'],
        'en': ['Used coffee'],
    },
    'coffee_programs': {
        'ru': ['Режимы', 'Предустановленные программы'],
        'ua': ['Режими', 'Предустановлені програми'],
        'en': ['Modes', 'Preinstalled programs'],
    },
    'milk_drinks': {
        'ru': ['Приготовление молочных напитков'],
        'ua': ['Приготування молочних напоїв'],
        'en': ['Milk drinks preparation'],
    },
    'coffee_adjustments': {
        'ru': ['Регулировки'],
        'ua': ['Регулювання'],
        'en': ['Adjustments'],
    },
    'coffee_features': {
        'ru': ['Функции и возможности'],
        'ua': ['Функції та можливості'],
        'en': ['Features'],
    },
    'compatible_capsules': {
        'ru': ['Совместимые капсулы'],
        'ua': ['Сумісні капсули'],
        'en': ['Compatible capsules'],
    },
    'servings_per_cycle': {
        'ru': ['Порций за 1 раз'],
        'ua': ['Порцій за 1 раз'],
        'en': ['Servings per cycle', 'Servings per cycle (espresso)'],
    },
    'coffee_pressure': {
        'ru': ['Давление'],
        'ua': ['Тиск'],
        'en': ['Pressure'],
    },
    'coffee_power': {
        'ru': ['Потребляемая мощность', 'Мощность (Вт)'],
        'ua': ['Споживана потужність', 'Потужність (Вт)'],
        'en': ['Power consumption', 'Power'],
    },
    'coffee_water_tank': {
        'ru': ['Резервуар для воды', 'Объем резервуара (л)'],
        'ua': ['Резервуар для води', "Об'єм резервуара (л)", 'Об’єм резервуара (л)'],
        'en': ['Water tank', 'Reservoir volume'],
    },
    'grinder_capacity': {
        'ru': ['Емкость кофемолки'],
        'ua': ['Об’єм кавомолки', "Об'єм кавомолки"],
        'en': ['Coffee grinder capacity'],
    },
    'built_in_grinder': {
        'ru': ['Встроенная кофемолка'],
        'ua': ['Вбудована кавомолка'],
        'en': ['Built-in coffee grinder'],
    },
    'hopper_count': {
        'ru': ['Количество бункеров'],
        'ua': ['Кількість бункерів'],
        'en': ['Number of hoppers'],
    },
    'custom_program': {
        'ru': ['Своя программа'],
        'ua': ['Своя програма'],
        'en': ['Custom programme', 'Custom program'],
    },
    'user_profiles': {
        'ru': ['Профилей пользователя'],
        'ua': ['Профілів користувача', 'Профілі користувачів'],
        'en': ['User profiles'],
    },
    'smartphone_control': {
        'ru': ['Управление со смартфона'],
        'ua': ['Керування зі смартфона'],
        'en': ['Control via smartphone', 'Smartphone control'],
    },
    'milk_tank': {
        'ru': ['Резервуар для молока'],
        'ua': ['Резервуар для молока'],
        'en': ['Milk tank'],
    },
    'burner_controls': {
        'ru': ['Управление конфорками'],
        'ua': ['Управління конфорками'],
        'en': ['Burners controls', 'Burner controls'],
    },
    'hob_surface': {
        'ru': ['Рабочая поверхность'],
        'ua': ['Робоча поверхня'],
        'en': ['Hob material'],
    },
    'cooker_design': {
        'ru': ['Оформление'],
        'ua': ['Оформлення'],
        'en': ['Design'],
    },
    'oven_type': {
        'ru': ['Тип духовки'],
        'ua': ['Тип духовки'],
        'en': ['Oven'],
    },
    'oven_capacity': {
        'ru': ['Объем духовки'],
        'ua': ['Об’єм духовки', "Об'єм духовки"],
        'en': ['Oven capacity'],
    },
    'oven_power': {
        'ru': ['Мощность духовки'],
        'ua': ['Потужність духовки'],
        'en': ['Oven power'],
    },
    'connected_load': {
        'ru': ['Мощность подключения'],
        'ua': ['Потужність підключення'],
        'en': ['Connected load'],
    },
    'burner_grates': {
        'ru': ['Решетки конфорок'],
        'ua': ['Решітки конфорок'],
        'en': ['Burner grates'],
    },
    'frame': {
        'ru': ['Рамка'],
        'ua': ['Рамка'],
        'en': ['Frame'],
    },
    'cooker_lid': {
        'ru': ['Крышка'],
        'ua': ['Кришка'],
        'en': ['Lid'],
    },
    'country_of_origin': {
        'ru': ['Страна производства'],
        'ua': ['Країна виробництва'],
        'en': ['Country of origin'],
    },
    'energy_class': {
        'ru': ['Класс энергопотребления'],
        'ua': ['Клас енергоспоживання'],
        'en': ['Energy class'],
    },
    'dishwasher_place_settings': {
        'ru': ['Кол-во комплектов посуды'],
        'ua': ['Кількість комплектів посуду'],
        'en': ['Place settings'],
    },
    'dishwasher_programs': {
        'ru': ['Ключевые программы'],
        'ua': ['Ключові програми'],
        'en': ['Key programmes', 'Key programs'],
    },
    'dishwasher_dryer_type': {
        'ru': ['Сушка'],
        'ua': ['Сушіння'],
        'en': ['Dryer type'],
    },
    'dishwasher_water_consumption': {
        'ru': ['Расход воды за цикл'],
        'ua': ['Витрата води за цикл'],
        'en': ['Water consumption per cycle'],
    },
    'dishwasher_controls': {
        'ru': ['Управление'],
        'ua': ['Управління'],
        'en': ['Controls'],
    },
    'dishwasher_hot_water_supply': {
        'ru': ['Подключения к горячей воде', 'Подключение к горячей воде'],
        'ua': ['Підключення до гарячої води'],
        'en': ['Hot water supply'],
    },
    'dishwasher_no_plumbing': {
        'ru': ['Не требуется водопровод'],
        'ua': ['Не потрібний водопровід'],
        'en': ['No plumbing'],
    },
    'dishwasher_end_signal': {
        'ru': ['Сигнал окончания работы'],
        'ua': ['Сигнал закінчення роботи'],
        'en': ['End-of-cycle signal'],
    },
    'dishwasher_energy_class_new': {
        'ru': ['Класс энергопотребления (new)'],
        'ua': ['Клас енергоспоживання (new)'],
        'en': ['Energy class (new)'],
    },
    'fridge_chambers': {
        'ru': ['Количество камер'],
        'ua': ['Кількість камер'],
        'en': ['Number of chambers'],
    },
    'fridge_freezer_position': {
        'ru': ['Морозильная камера'],
        'ua': ['Морозильна камера'],
        'en': ['Freezer compartment'],
    },
    'fridge_no_frost': {
        'ru': ['No Frost'],
        'ua': ['No Frost'],
        'en': ['No Frost'],
    },
    'fridge_functions': {
        'ru': ['Функции'],
        'ua': ['Функції'],
        'en': ['Features'],
    },
    'fridge_additional': {
        'ru': ['Дополнительно'],
        'ua': ['Додатково'],
        'en': ['More features'],
    },
    'fridge_storage': {
        'ru': ['Отсеки для хранения'],
        'ua': ['Відсіки для зберігання'],
        'en': ['Storage compartments'],
    },
    'fridge_controls': {
        'ru': ['Управление'],
        'ua': ['Управління'],
        'en': ['Controls'],
    },
    'fridge_energy_class_new': {
        'ru': ['Класс энергопотребления (new)'],
        'ua': ['Клас енергоспоживання (new)'],
        'en': ['Energy class (new)'],
    },
    'climate_class': {
        'ru': ['Климатический класс'],
        'ua': ['Кліматичний клас'],
        'en': ['Climate class'],
    },
    'fridge_capacity': {
        'ru': ['Объем холодильной камеры'],
        'ua': ["Об'єм холодильної камери", 'Об’єм холодильної камери'],
        'en': ['Refrigerator capacity'],
    },
    'fridge_shelves': {
        'ru': ['Полок'],
        'ua': ['Полиць'],
        'en': ['Number of shelves', 'Refrigerator shelves'],
    },
    'freezer_capacity': {
        'ru': ['Объем морозильной камеры'],
        'ua': ["Об'єм морозильної камери", 'Об’єм морозильної камери'],
        'en': ['Freezer capacity'],
    },
    'freezer_drawers': {
        'ru': ['Отделений морозильной камеры'],
        'ua': ['Відділень морозильної камери'],
        'en': ['Freezer drawers'],
    },
    'fridge_autonomy_time': {
        'ru': ['Время сохранения холода'],
        'ua': ['Час збереження холоду'],
        'en': ['Autonomy time'],
    },
    'freeze_temperature': {
        'ru': ['Температура морозилки'],
        'ua': ['Температура морозилки'],
        'en': ['Freezer temperature'],
    },
    'freeze_power': {
        'ru': ['Мощность замораживания'],
        'ua': ['Потужність заморожування'],
        'en': ['Freeze capacity'],
    },
    'cooling_circuits': {
        'ru': ['Контуров охлаждения'],
        'ua': ['Контурів охолодження'],
        'en': ['Number of cooling circuits'],
    },
    'compressors': {
        'ru': ['Компрессоров'],
        'ua': ['Компресорів'],
        'en': ['Number of compressors'],
    },
    'fast_cool': {
        'ru': ['Быстрое охлаждение'],
        'ua': ['Швидке охолодження'],
        'en': ['Fast cool'],
    },
    'fast_freeze': {
        'ru': ['Быстрая заморозка'],
        'ua': ['Швидка заморозка'],
        'en': ['Fast freeze'],
    },
    'dynamic_cooling': {
        'ru': ['Динамическое охлаждение'],
        'ua': ['Динамічне охолодження'],
        'en': ['Dynamic air cooling'],
    },
    'water_dispenser': {
        'ru': ['Диспенсер холодной воды'],
        'ua': ['Диспенсер холодної води'],
        'en': ['Water dispenser'],
    },
    'ice_maker': {
        'ru': ['Ледогенератор'],
        'ua': ['Льодогенератор'],
        'en': ['Ice maker'],
    },
    'hob_device': {
        'ru': ['Устройство'],
        'ua': ['Тип пристрою'],
        'en': ['Product type'],
    },
    'hob_controls': {
        'ru': ['Управление'],
        'ua': ['Управління'],
        'en': ['Controls'],
    },
    'hob_power_levels': {
        'ru': ['Уровней мощности конфорок'],
        'ua': ['Рівнів потужності конфорок'],
        'en': ['Number of power levels'],
    },
    'hob_dimensions_wd': {
        'ru': ['Габариты (ШхГ)'],
        'ua': ['Габарити (ШхГ)'],
        'en': ['Dimensions (WxD)'],
    },
    'hob_cutout_wd': {
        'ru': ['Размеры для встраивания (ШхГ)'],
        'ua': ['Розміри для вбудовування (ШхГ)'],
        'en': ['Cut-out dimensions (WxD)'],
    },
    'display': {
        'ru': ['Дисплей'],
        'ua': ['Дисплей'],
        'en': ['Display', 'Digital display'],
    },
    'oven_cleaning': {
        'ru': ['Тип очистки внутренней поверхности', 'Очистка внутренних стенок'],
        'ua': ['Тип очищення внутрішньої поверхні', 'Очищення духовки', 'Очищення внутрішніх стінок'],
        'en': ['Oven cleaning'],
    },
    'oven_cooking_modes': {
        'ru': ['Режимы готовки'],
        'ua': ['Режими готування'],
        'en': ['Cooking modes'],
    },
    'oven_modes_count': {
        'ru': ['Кол-во режимов'],
        'ua': ['Кількість режимів'],
        'en': ['Number of modes'],
    },
    'oven_temperature': {
        'ru': ['Температура готовки'],
        'ua': ['Температура готування'],
        'en': ['Cooking temperature'],
    },
    'oven_features_list': {
        'ru': ['Функции'],
        'ua': ['Функції'],
        'en': ['Features'],
    },
    'oven_controls': {
        'ru': ['Органы управления'],
        'ua': ['Органи управління'],
        'en': ['Controls'],
    },
    'oven_guides': {
        'ru': ['Направляющие противней'],
        'ua': ['Напрямні дек'],
        'en': ['Guides'],
    },
    'oven_cutout_hwd': {
        'ru': ['Размеры для встраивания (ВхШхГ)'],
        'ua': ['Розміри для монтажу (ВхШхГ)', 'Розміри для вбудовування (ВхШхГ)'],
        'en': ['Cut-out dimensions (HxWxD)'],
    },
    'oven_automatic_programs': {
        'ru': ['Автоматических программ'],
        'ua': ['Автоматичних програм'],
        'en': ['Number of automatic programmes', 'Number of automatic programs'],
    },
    'wash_type': {
        'ru': ['Тип загрузки'],
        'ua': ['Тип завантаження'],
        'en': ['Loading type', 'Product type'],
    },
    'wash_capacity': {
        'ru': ['Загрузка'],
        'ua': ['Завантаження'],
        'en': ['Capacity'],
    },
    'wash_drying_capacity': {
        'ru': ['Загрузка для сушки'],
        'ua': ['Завантаження для сушіння'],
        'en': ['Drying capacity'],
    },
    'wash_dryer_presence': {
        'ru': ['Сушилка', 'Сушка'],
        'ua': ['Сушка', 'Сушіння', 'Сушарка'],
        'en': ['Dryer', 'Drying'],
    },
    'wash_spin_speed': {
        'ru': ['Макс. скорость отжима'],
        'ua': ['Макс. швидкість віджимання'],
        'en': ['Spin speed', 'Max. spin speed'],
    },
    'wash_programmes': {
        'ru': ['Дополнительные программы'],
        'ua': ['Додаткові програми'],
        'en': ['Programmes', 'Programs', 'Additional programmes', 'Additional programs'],
    },
    'wash_steam': {
        'ru': ['Стирка паром'],
        'ua': ['Прання паром'],
        'en': ['Steam wash'],
    },
    'wash_direct_injection': {
        'ru': ['Система прямого впрыска'],
        'ua': ['Система прямого впорскування'],
        'en': ['Direct injection system'],
    },
    'wash_auto_dosing': {
        'ru': ['Автоматическое дозирование'],
        'ua': ['Автоматичне дозування'],
        'en': ['Automatic dosing'],
    },
    'wash_controls': {
        'ru': ['Управление'],
        'ua': ['Управління'],
        'en': ['Controls'],
    },
    'wash_smartphone_control': {
        'ru': ['Управление со смартфона'],
        'ua': ['Керування зі смартфона'],
        'en': ['Smartphone control'],
    },
    'wash_leak_protection': {
        'ru': ['Защита от протечек'],
        'ua': ['Захист від протікань'],
        'en': ['Leak protection'],
    },
    'wash_imbalance_control': {
        'ru': ['Контроль дисбаланса'],
        'ua': ['Контроль дисбалансу'],
        'en': ['Unbalance control'],
    },
    'wash_foam_control': {
        'ru': ['Контроль пенообразования'],
        'ua': ['Контроль піноутворення'],
        'en': ['Anti-foam control', 'Foam control'],
    },
    'wash_heating_element_material': {
        'ru': ['Материал ТЭНа'],
        'ua': ['Матеріал ТЕНу'],
        'en': ['Heating element material'],
    },
    'wash_tank_material': {
        'ru': ['Материал бака'],
        'ua': ['Матеріал бака'],
        'en': ['Tank material'],
    },
    'wash_drum_lighting': {
        'ru': ['Подсветка барабана'],
        'ua': ['Підсвічування барабана'],
        'en': ['Drum lighting'],
    },
    'wash_inverter_motor': {
        'ru': ['Инверторный двигатель'],
        'ua': ['Інверторний двигун'],
        'en': ['Inverter motor'],
    },
    'wash_dimensions_hwd': {
        'ru': ['Габариты (ВхШхГ)'],
        'ua': ['Габарити (ВхШхГ)'],
        'en': ['Dimensions (HxWxD)'],
    },
    'wash_energy_class_new': {
        'ru': ['Класс энергопотребления (new)'],
        'ua': ['Клас енергоспоживання (new)'],
        'en': ['Energy class (new)'],
    },
    'wash_energy_class_old': {
        'ru': ['Класс энергопотребления'],
        'ua': ['Клас енергоспоживання'],
        'en': ['Energy class'],
    },
    'wash_spin_class': {
        'ru': ['Класс отжима'],
        'ua': ['Клас віджимання'],
        'en': ['Spin class'],
    },
    'wash_noise_level': {
        'ru': ['Уровень шума (отжим)'],
        'ua': ['Рівень шуму (віджимання)'],
        'en': ['Noise level (spin)', 'Noise level'],
    },
    'wash_water_consumption': {
        'ru': ['Расход воды за цикл'],
        'ua': ['Витрата води за цикл'],
        'en': ['Water consumption', 'Water consumption per cycle'],
    },
    'wash_door_opening': {
        'ru': ['Открытие дверцы'],
        'ua': ['Відкриття дверцят'],
        'en': ['Door opening'],
    },
    'wash_opening_angle': {
        'ru': ['Угол открытия'],
        'ua': ['Кут відкриття'],
        'en': ['Opening angle'],
    },
    'hob_type': {
        'ru': ['Тип варочной поверхности', 'Тип поверхности'],
        'ua': ['Тип варильної поверхні', 'Тип поверхні'],
        'en': ['Burner type', 'Hob type', 'Surface type'],
    },
    'cooker_functions': {
        'ru': ['Функции'],
        'ua': ['Функції'],
        'en': ['Functions'],
    },
    'burners_power': {
        'ru': ['Мощность конфорок'],
        'ua': ['Потужність конфорок'],
        'en': ['Burner power'],
    },
    'dimensions_hwd': {
        'ru': ['Габариты (ВхШхГ)'],
        'ua': ['Габарити (ВхШхГ)'],
        'en': ['Dimensions (HxWxD)'],
    },
    'auto_power_off': {
        'ru': ['Автоматическое отключение'],
        'ua': ['Автоматичне вимкнення'],
        'en': ['Auto switch-off'],
    },
    'child_lock': {
        'ru': ['Защита от детей'],
        'ua': ['Захист від дітей'],
        'en': ['Child lock'],
    },
    'microwave_capacity': {
        'ru': ['Объем'],
        'ua': ['Об’єм', "Об'єм"],
        'en': ['Capacity'],
    },
    'microwave_power': {
        'ru': ['Мощность микроволн', 'Мощность'],
        'ua': ['Потужність мікрохвиль', 'Потужність'],
        'en': ['Microwave power', 'Power'],
    },
    'microwave_features': {
        'ru': ['Функции и возможности', 'Функции'],
        'ua': ['Функції та можливості', 'Функції'],
        'en': ['Features'],
    },
    'microwave_extra': {
        'ru': ['Дополнительно'],
        'ua': ['Додатково'],
        'en': ['More features'],
    },
    'microwave_controls': {
        'ru': ['Органы управления', 'Управление'],
        'ua': ['Органи управління', 'Управління'],
        'en': ['Controls'],
    },
    'microwave_inner_coating': {
        'ru': ['Внутреннее покрытие'],
        'ua': ['Внутрішнє покриття'],
        'en': ['Inner coating', 'Interior coating'],
    },
    'microwave_door': {
        'ru': ['Дверца', 'Навеска дверцы'],
        'ua': ['Дверцята', 'Навішування дверцят'],
        'en': ['Door', 'Door hinge'],
    },
    'microwave_door_opening': {
        'ru': ['Открытие дверцы', 'Открывание дверцы'],
        'ua': ['Відкриття дверцят'],
        'en': ['Door opening'],
    },
    'microwave_turntable_diameter': {
        'ru': ['Диаметр столика', 'Диаметр поворотного столика', 'Диаметр поддона'],
        'ua': ['Діаметр столика', 'Діаметр поворотного столика', 'Діаметр піддона'],
        'en': ['Turntable diameter', 'Tray diameter'],
    },
    'flex_zone': {
        'ru': ['Адаптивная зона (FlexZone)'],
        'ua': ['Адаптивна зона (FlexZone)'],
        'en': ['Adaptive zone (FlexZone)'],
    },
    'bridge_mode': {
        'ru': ['Режим «мост» (Bridge)'],
        'ua': ['Режим міст (Bridge)'],
        'en': ['Bridge mode'],
    },
    'oval_zone': {
        'ru': ['Овальная зона'],
        'ua': ['Овальна зона'],
        'en': ['Oval dual zone'],
    },
    'contour_burner': {
        'ru': ['Контурная конфорка'],
        'ua': ['Контурна конфорка'],
        'en': ['Dual-circuit zone', 'Contour burner'],
    },
    'wok_burners': {
        'ru': ['Из них WOK-конфорок (турбо)', 'Из них турбоконфорок'],
        'ua': ['З них WOK-конфорок (турбо)', 'З них турбоконфорок'],
        'en': ['Turbo burner', 'WOK burners'],
    },
    'residual_heat': {
        'ru': ['Индикатор остаточного тепла'],
        'ua': ['Індикатор залишкового тепла'],
        'en': ['Heat indicator'],
    },
    'glass_count': {
        'ru': ['Кол-во стекол дверцы'],
        'ua': ['Кількість стекол дверцят', 'Кількість скел дверцят'],
        'en': ['Glass door count'],
    },
    'auto_ignition': {
        'ru': ['Автоподжиг'],
        'ua': ['Автопідпал'],
        'en': ['Auto ignition'],
    },
    'gas_control': {
        'ru': ['Газ-контроль'],
        'ua': ['Газ-контроль'],
        'en': ['Gas control'],
    },
    'thermoprobe': {
        'ru': ['Термощуп'],
        'ua': ['Термощуп'],
        'en': ['Temperature probe'],
    },
    'door_closer': {
        'ru': ['Автодоводчик дверцы'],
        'ua': ['Автодоводчик дверцят'],
        'en': ['Door closer'],
    },
    'gas_burners': {
        'ru': ['Кол-во газовых конфорок'],
        'ua': ['Кількість газових конфорок'],
        'en': ['Gas burners count'],
    },
    'induction_burners': {
        'ru': ['Кол-во индукционных конфорок'],
        'ua': ['Кількість індукційних конфорок'],
        'en': ['Induction burners count'],
    },
    'hilight_burners': {
        'ru': ['Кол-во Hi-Light конфорок'],
        'ua': ['Кількість Hi-Light конфорок'],
        'en': ['Hi-Light burners count'],
    },
    'halogen_burners': {
        'ru': ['Кол-во галогенных конфорок'],
        'ua': ['Кількість галогенних конфорок'],
        'en': ['Halogen burners count'],
    },
    'cast_iron_burners': {
        'ru': ['Кол-во чугунных конфорок'],
        'ua': ['Кількість чавунних конфорок'],
        'en': ['Solid plate burners count', 'Cast iron burners count'],
    },
    'spiral_burners': {
        'ru': ['Кол-во спиральных конфорок'],
        'ua': ['Кількість спіральних конфорок'],
        'en': ['Spiral burners count'],
    },
}

MATCH_STOP_WORDS = {
    'ru': {'для', 'их', 'и', 'на', 'по', 'все', 'всех', 'всеx', 'не', 'роботы', 'робот'},
    'ua': {'для', 'їх', 'і', 'на', 'по', 'усі', 'всі', 'не', 'роботи', 'робот'},
    'en': {'for', 'and', 'the', 'all', 'not', 'with', 'their', 'robot', 'robots'},
}

FILTER_LABELS = {
    'ru': {
        'filters_title': 'Фильтры',
        'brands_title': 'Бренды',
        'show_label': 'Показать',
        'apply_label': 'Применить',
        'reset_label': 'Сбросить',
        'all_brands_label': 'Все бренды',
    },
    'ua': {
        'filters_title': 'Фільтри',
        'brands_title': 'Бренди',
        'show_label': 'Показати',
        'apply_label': 'Застосувати',
        'reset_label': 'Скинути',
        'all_brands_label': 'Усі бренди',
    },
    'en': {
        'filters_title': 'Filters',
        'brands_title': 'Brands',
        'show_label': 'Show',
        'apply_label': 'Apply',
        'reset_label': 'Reset',
        'all_brands_label': 'All brands',
    },
}

BOOLEAN_TRUE_VALUES = {
    'ru': {'да', '+', 'есть', 'в комплекте'},
    'ua': {'так', '+', 'є', 'у комплекті'},
    'en': {'yes', '+', 'included'},
}


def get_filter_labels(lang):
    return FILTER_LABELS.get(lang, FILTER_LABELS['en'])


@lru_cache(maxsize=1)
def _load_vacuum_filter_groups():
    return _load_category_filter_groups('cleaners')


@lru_cache(maxsize=None)
def _load_category_filter_groups(category_id):
    config = CATEGORY_FILTER_CONFIGS.get(category_id)
    if config is None:
        return {lang: [] for lang in LANGUAGE_MARKERS}

    file_path = os.path.join(settings.BASE_DIR, 'filters', config['file_name'])
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file.readlines()]

    groups_by_lang = {lang: [] for lang in LANGUAGE_MARKERS}
    current_lang = None
    current_group = None

    for line in lines:
        if not line:
            continue

        marker_lang = next((lang for lang, marker in LANGUAGE_MARKERS.items() if line == marker), None)
        if marker_lang:
            current_lang = marker_lang
            current_group = None
            continue

        if current_lang is None:
            continue

        if line.startswith('☐'):
            option_label = line.replace('☐', '', 1).strip()
            if current_group is not None and option_label:
                current_group['options'].append(option_label)
            continue

        current_group = {
            'title': line,
            'options': [],
        }
        groups_by_lang[current_lang].append(current_group)

    result = {}
    for lang, groups in groups_by_lang.items():
        normalized_groups = []
        for index, group in enumerate(groups[:len(config['keys'])]):
            key = config['keys'][index]
            normalized_groups.append({
                'key': key,
                'param': f"{config['param_prefix']}_{key}",
                'title': group['title'],
                'collapse_id': f"{lang}-{config['param_prefix']}-{key}",
                'options': [
                    {
                        'value': str(option_index),
                        'label': option_label,
                    }
                    for option_index, option_label in enumerate(group['options'])
                ],
            })
        result[lang] = normalized_groups
    return result


def get_vacuum_filter_groups(lang):
    return deepcopy(_load_vacuum_filter_groups().get(lang, []))


def get_coffee_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('coffeemachines').get(lang, []))


def get_cooker_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('cookers').get(lang, []))


def get_dishwasher_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('dishwashers').get(lang, []))


def get_fridge_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('fridges').get(lang, []))


def get_hob_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('hobs').get(lang, []))


def get_oven_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('ovens').get(lang, []))


def get_wash_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('wash').get(lang, []))


def get_microwave_filter_groups(lang):
    return deepcopy(_load_category_filter_groups('microwaves').get(lang, []))


def get_section_filter_groups(category_id, lang):
    if category_id == 'cleaners':
        return get_vacuum_filter_groups(lang)
    if category_id == 'coffeemachines':
        return get_coffee_filter_groups(lang)
    if category_id == 'cookers':
        return get_cooker_filter_groups(lang)
    if category_id == 'dishwashers':
        return get_dishwasher_filter_groups(lang)
    if category_id == 'fridges':
        return get_fridge_filter_groups(lang)
    if category_id == 'hobs':
        return get_hob_filter_groups(lang)
    if category_id == 'ovens':
        return get_oven_filter_groups(lang)
    if category_id in {'wash', 'washers'}:
        return get_wash_filter_groups(lang)
    if category_id == 'microwaves':
        return get_microwave_filter_groups(lang)
    return []


def enrich_filter_groups(groups, selected_values):
    for group in groups:
        current_values = set(selected_values.get(group['param'], []))
        group['has_selected'] = bool(current_values)
        for option in group['options']:
            option['selected'] = option['value'] in current_values
    return groups


def apply_vacuum_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_group_option)


def apply_coffee_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_coffee_group_option)


def apply_cooker_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_cooker_group_option)


def apply_dishwasher_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_dishwasher_group_option)


def apply_fridge_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_fridge_group_option)


def apply_hob_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_hob_group_option)


def apply_oven_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_oven_group_option)


def apply_wash_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_wash_group_option)


def apply_microwave_filters(products, lang, groups, selected_values):
    return _apply_filters(products, lang, groups, selected_values, _matches_microwave_group_option)


def apply_section_filters(products, category_id, lang, groups, selected_values):
    if category_id == 'cleaners':
        return apply_vacuum_filters(products, lang, groups, selected_values)
    if category_id == 'coffeemachines':
        return apply_coffee_filters(products, lang, groups, selected_values)
    if category_id == 'cookers':
        return apply_cooker_filters(products, lang, groups, selected_values)
    if category_id == 'dishwashers':
        return apply_dishwasher_filters(products, lang, groups, selected_values)
    if category_id == 'fridges':
        return apply_fridge_filters(products, lang, groups, selected_values)
    if category_id == 'hobs':
        return apply_hob_filters(products, lang, groups, selected_values)
    if category_id == 'ovens':
        return apply_oven_filters(products, lang, groups, selected_values)
    if category_id in {'wash', 'washers'}:
        return apply_wash_filters(products, lang, groups, selected_values)
    if category_id == 'microwaves':
        return apply_microwave_filters(products, lang, groups, selected_values)
    return products


def _apply_filters(products, lang, groups, selected_values, match_func):
    filtered_products = []
    for product in products:
        if _product_matches_groups(product, lang, groups, selected_values, match_func):
            filtered_products.append(product)
    return filtered_products


def _product_matches_groups(product, lang, groups, selected_values, match_func):
    for group in groups:
        current_values = selected_values.get(group['param'], [])
        if not current_values:
            continue
        option_map = {option['value']: option for option in group['options']}
        if not any(
            match_func(product, lang, group['key'], option_map[option_value]['label'], option_map[option_value]['value'])
            for option_value in current_values
            if option_value in option_map
        ):
            return False
    return True


def _matches_group_option(product, lang, group_key, option_label, option_value):
    if group_key in {
        'motor_power',
        'suction_power_w',
        'suction_force_pa',
        'noise_level',
        'runtime',
        'dust_capacity',
        'water_tank',
        'cable_length',
        'weight',
    }:
        return _matches_numeric_group(product, lang, group_key, option_label)

    if group_key == 'robot_height':
        return _matches_robot_height(product, lang, option_label)

    if group_key == 'cleaning':
        return _matches_field_label(product, lang, 'cleaning', option_label)

    if group_key == 'power_source':
        return _matches_field_label(product, lang, 'power_source', option_label)

    if group_key == 'dust_collector':
        return _matches_field_label(product, lang, 'dust_collector', option_label)

    if group_key == 'battery_type':
        return _matches_field_label(product, lang, 'battery_type', option_label)

    if group_key == 'vacuum_type':
        return _matches_vacuum_type(product, lang, int(option_value))

    if group_key == 'floor_washing':
        return _matches_floor_washing(product, lang, int(option_value))

    if group_key == 'features':
        return _matches_features(product, lang, option_label, int(option_value))

    if group_key == 'nozzles':
        return _matches_nozzles(product, lang, option_label)

    if group_key == 'robot_features':
        return _matches_robot_features(product, lang, option_label, int(option_value))

    if group_key == 'extra':
        return _matches_extra(product, lang, option_label, int(option_value))

    if group_key == 'battery':
        return _matches_battery(product, lang, option_label, int(option_value))

    if group_key == 'robot_shape':
        return _matches_robot_shape(product, lang, option_label)

    return False


def _matches_coffee_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'coffee_type':
        return _matches_coffee_type(product, lang, int(option_value))

    if group_key == 'used_coffee':
        return _matches_field_label(product, lang, 'used_coffee', option_label)

    if group_key == 'coffee_programs':
        return _matches_coffee_programs(product, lang, option_label, int(option_value))

    if group_key == 'milk_drinks':
        return _matches_coffee_milk_drinks(product, lang, option_label, int(option_value))

    if group_key == 'coffee_adjustments':
        return _matches_field_label(product, lang, 'coffee_adjustments', option_label)

    if group_key == 'coffee_features':
        return _matches_coffee_features(product, lang, option_label, int(option_value))

    if group_key == 'compatible_capsules':
        return _matches_field_label(product, lang, 'compatible_capsules', option_label)

    if group_key == 'servings_per_cycle':
        return _matches_numeric_group(product, lang, 'servings_per_cycle', option_label)

    if group_key == 'coffee_pressure':
        return _matches_numeric_group(product, lang, 'coffee_pressure', option_label)

    if group_key == 'coffee_power':
        return _matches_numeric_group(
            product,
            lang,
            'coffee_power',
            option_label,
            {
                ('квт', 'kw'): 1000,
                ('вт', 'w'): 1,
            },
        )

    if group_key == 'coffee_water_tank':
        return _matches_numeric_group(
            product,
            lang,
            'coffee_water_tank',
            option_label,
            {
                ('мл', 'ml'): 1,
                (' л', 'l', 'lt'): 1000,
            },
        )

    if group_key == 'grinder_capacity':
        return _matches_numeric_group(product, lang, 'grinder_capacity', option_label)

    return False


def _matches_cooker_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'cooker_type':
        return _matches_cooker_type(product, lang, int(option_value))

    if group_key == 'burner_type':
        return _matches_burner_type(product, lang, int(option_value))

    if group_key == 'burners_count':
        return _matches_burners_count(product, option_label)

    if group_key == 'hob_surface':
        return _matches_field_label(product, lang, 'hob_surface', option_label)

    if group_key == 'cooker_design':
        return _matches_field_label(product, lang, 'cooker_design', option_label)

    if group_key == 'small_burner_power':
        return _matches_cooker_burner_power(product, lang, option_label, 'min')

    if group_key == 'big_burner_power':
        return _matches_cooker_burner_power(product, lang, option_label, 'max')

    if group_key == 'oven_type':
        return _matches_field_label(product, lang, 'oven_type', option_label)

    if group_key == 'oven_capacity':
        return _matches_numeric_group(product, lang, 'oven_capacity', option_label)

    if group_key == 'oven_power':
        return _matches_numeric_group(product, lang, 'oven_power', option_label, {('квт', 'kw'): 1, ('вт', 'w'): 0.001})

    if group_key == 'cooker_features':
        return _matches_cooker_features(product, lang, option_label, int(option_value))

    if group_key == 'oven_features':
        return _matches_oven_features(product, lang, option_label, int(option_value))

    if group_key == 'release_year':
        return _matches_release_year(product, lang, int(option_value))

    if group_key == 'oven_cleaning':
        return _matches_field_label(product, lang, 'oven_cleaning', option_label)

    if group_key == 'burner_controls':
        return _matches_field_label(product, lang, 'burner_controls', option_label)

    if group_key == 'combined_burners':
        return _matches_combined_burners(product, int(option_value))

    if group_key == 'energy_class':
        return _matches_field_label(product, lang, 'energy_class', option_label)

    if group_key == 'connected_load':
        return _matches_numeric_group(product, lang, 'connected_load', option_label, {('квт', 'kw'): 1, ('вт', 'w'): 0.001})

    if group_key == 'cooker_width':
        return _matches_cooker_dimension(product, lang, option_label, 1)

    if group_key == 'cooker_depth':
        return _matches_cooker_dimension(product, lang, option_label, 2)

    if group_key == 'burner_grates':
        return _matches_field_label(product, lang, 'burner_grates', option_label)

    if group_key == 'cooker_lid':
        return _matches_field_label(product, lang, 'cooker_lid', option_label)

    if group_key == 'country_of_origin':
        return _matches_field_label(product, lang, 'country_of_origin', option_label)

    return False


def _matches_dishwasher_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'dishwasher_format':
        return _matches_dishwasher_format(product, lang, int(option_value))

    if group_key == 'dishwasher_width':
        return _matches_dishwasher_width(product, lang, int(option_value))

    if group_key == 'dishwasher_place_settings':
        return _matches_numeric_group(product, lang, 'dishwasher_place_settings', option_label)

    if group_key == 'dishwasher_programs':
        return _matches_dishwasher_programs(product, lang, option_label, int(option_value))

    if group_key == 'dishwasher_features':
        return _matches_dishwasher_features(product, lang, option_label, int(option_value))

    if group_key == 'dishwasher_dryer_type':
        return _matches_field_label(product, lang, 'dishwasher_dryer_type', option_label)

    if group_key == 'dishwasher_water_consumption':
        return _matches_numeric_group(product, lang, 'dishwasher_water_consumption', option_label)

    if group_key == 'dishwasher_energy_class':
        return _matches_dishwasher_energy_class(product, lang, option_label, int(option_value))

    if group_key == 'dishwasher_noise_level':
        return _matches_numeric_group(product, lang, 'noise_level', option_label)

    if group_key == 'dishwasher_controls':
        return _matches_field_label(product, lang, 'dishwasher_controls', option_label)

    if group_key == 'dishwasher_country_of_origin':
        return _matches_field_label(product, lang, 'country_of_origin', option_label)

    if group_key == 'dishwasher_release_year':
        return _matches_release_year(product, lang, int(option_value))

    return False


def _matches_fridge_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'fridge_type':
        return _matches_fridge_type(product, lang, int(option_value))

    if group_key == 'fridge_chambers':
        return _matches_fridge_chambers(product, lang, int(option_value))

    if group_key == 'fridge_freezer_position':
        return _matches_fridge_freezer_position(product, lang, int(option_value))

    if group_key == 'fridge_features':
        return _matches_fridge_features(product, lang, option_label, int(option_value))

    if group_key == 'fridge_compartments':
        return _matches_fridge_compartments(product, lang, option_label, int(option_value))

    if group_key == 'fridge_additional':
        return _matches_fridge_additional(product, lang, option_label, int(option_value))

    if group_key == 'fridge_height':
        return _matches_fridge_height(product, lang, int(option_value))

    if group_key == 'fridge_width':
        return _matches_fridge_width(product, lang, int(option_value))

    if group_key == 'fridge_energy_class':
        return _matches_fridge_energy_class(product, lang, int(option_value))

    if group_key == 'fridge_release_year':
        return _matches_release_year(product, lang, int(option_value))

    if group_key == 'fridge_climate_class':
        return _matches_field_label(product, lang, 'climate_class', option_label)

    if group_key == 'fridge_controls':
        return _matches_field_label(product, lang, 'fridge_controls', option_label)

    if group_key == 'fridge_capacity':
        return _matches_numeric_group(product, lang, 'fridge_capacity', option_label)

    if group_key == 'fridge_shelves':
        return _matches_numeric_group(product, lang, 'fridge_shelves', option_label)

    if group_key == 'freezer_capacity':
        return _matches_numeric_group(product, lang, 'freezer_capacity', option_label)

    if group_key == 'freezer_drawers':
        return _matches_fridge_freezer_drawers(product, lang, option_label)

    if group_key == 'fridge_autonomy_time':
        return _matches_numeric_group(product, lang, 'fridge_autonomy_time', option_label)

    if group_key == 'fridge_noise_level':
        return _matches_numeric_group(product, lang, 'noise_level', option_label)

    if group_key == 'fridge_depth':
        return _matches_fridge_depth(product, lang, int(option_value))

    if group_key == 'fridge_country_of_origin':
        return _matches_field_label(product, lang, 'country_of_origin', option_label)

    return False


def _matches_hob_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'hob_device':
        return _matches_hob_device(product, lang, int(option_value))

    if group_key == 'hob_burner_type':
        return _matches_hob_burner_type(product, lang, int(option_value))

    if group_key == 'hob_burners_count':
        return _matches_burners_count(product, option_label)

    if group_key == 'hob_surface':
        return _matches_field_label(product, lang, 'hob_surface', option_label)

    if group_key == 'hob_design':
        return _matches_hob_design(product, lang, int(option_value))

    if group_key == 'hob_controls':
        return _matches_hob_controls(product, lang, int(option_value))

    if group_key == 'hob_features':
        return _matches_hob_features(product, lang, option_label, int(option_value))

    if group_key == 'hob_extra':
        return _matches_hob_extra(product, lang, option_label, int(option_value))

    if group_key == 'hob_release_year':
        return _matches_release_year(product, lang, int(option_value))

    if group_key == 'hob_includes_burners':
        return _matches_hob_includes_burners(product, lang, int(option_value))

    if group_key == 'hob_combined_burners':
        return _matches_hob_combined_burners(product, lang, int(option_value))

    if group_key == 'hob_small_burner_power':
        return _matches_cooker_burner_power(product, lang, option_label, 'min')

    if group_key == 'hob_big_burner_power':
        return _matches_cooker_burner_power(product, lang, option_label, 'max')

    if group_key == 'hob_connected_load':
        return _matches_numeric_group(product, lang, 'connected_load', option_label, {('квт', 'kw'): 1, ('вт', 'w'): 0.001})

    if group_key == 'hob_width':
        return _matches_hob_dimension_bucket(product, lang, 'hob_dimensions_wd', 0, int(option_value))

    if group_key == 'hob_depth':
        return _matches_hob_dimension_bucket(product, lang, 'hob_dimensions_wd', 1, int(option_value))

    if group_key == 'hob_cutout_width':
        return _matches_hob_dimension_bucket(product, lang, 'hob_cutout_wd', 0, int(option_value))

    if group_key == 'hob_cutout_depth':
        return _matches_hob_dimension_bucket(product, lang, 'hob_cutout_wd', 1, int(option_value))

    if group_key == 'hob_frame':
        return _matches_hob_frame(product, lang, int(option_value))

    if group_key == 'hob_burner_grates':
        return _matches_field_label(product, lang, 'burner_grates', option_label)

    if group_key == 'hob_country_of_origin':
        return _matches_field_label(product, lang, 'country_of_origin', option_label)

    return False


def _matches_oven_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'oven_device_type':
        return _matches_oven_device_type(product, lang, int(option_value))

    if group_key == 'oven_capacity_filter':
        return _matches_numeric_group(product, lang, 'oven_capacity', option_label)

    if group_key == 'oven_cooking_modes':
        return _matches_oven_cooking_modes(product, lang, option_label, int(option_value))

    if group_key == 'oven_modes_count':
        return _matches_numeric_group(product, lang, 'oven_modes_count', option_label)

    if group_key == 'oven_min_temperature':
        return _matches_oven_temperature(product, lang, option_label, 'min')

    if group_key == 'oven_max_temperature':
        return _matches_oven_temperature(product, lang, option_label, 'max')

    if group_key == 'oven_features_list':
        return _matches_oven_section_features(product, lang, option_label, int(option_value))

    if group_key == 'oven_cleaning_type':
        return _matches_field_label(product, lang, 'oven_cleaning', option_label)

    if group_key == 'oven_switches':
        return _matches_field_label(product, lang, 'oven_controls', option_label)

    if group_key == 'oven_guides_filter':
        return _matches_field_label(product, lang, 'oven_guides', option_label)

    if group_key == 'oven_energy_class_filter':
        return _matches_field_label(product, lang, 'energy_class', option_label)

    if group_key == 'oven_connected_load_filter':
        return _matches_numeric_group(product, lang, 'connected_load', option_label, {('квт', 'kw'): 1, ('вт', 'w'): 0.001})

    if group_key == 'oven_height_filter':
        return _matches_oven_height(product, lang, int(option_value))

    if group_key == 'oven_width_filter':
        return _matches_oven_width(product, lang, int(option_value))

    if group_key == 'oven_cutout_depth':
        return _matches_oven_cutout_depth(product, lang, option_label)

    if group_key == 'oven_country_of_origin_filter':
        return _matches_field_label(product, lang, 'country_of_origin', option_label)

    return False


def _matches_wash_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'wash_type':
        return _matches_wash_type(product, lang, int(option_value))

    if group_key == 'wash_capacity':
        return _matches_numeric_group(product, lang, 'wash_capacity', option_label)

    if group_key == 'wash_drying_capacity':
        return _matches_numeric_group(product, lang, 'wash_drying_capacity', option_label)

    if group_key == 'wash_spin_speed':
        return _matches_numeric_group(product, lang, 'wash_spin_speed', option_label)

    if group_key == 'wash_features':
        return _matches_wash_features(product, lang, option_label, int(option_value))

    if group_key == 'wash_programmes':
        return _matches_wash_programmes(product, lang, option_label)

    if group_key == 'wash_controls':
        return _matches_wash_controls(product, lang, option_label, int(option_value))

    if group_key == 'wash_protection':
        return _matches_wash_protection(product, lang, option_label, int(option_value))

    if group_key == 'wash_depth':
        return _matches_wash_dimension(product, lang, option_label, 2)

    if group_key == 'wash_release_year':
        return _matches_release_year(product, lang, int(option_value))

    if group_key == 'wash_width':
        return _matches_wash_dimension(product, lang, option_label, 1)

    if group_key == 'wash_height':
        return _matches_wash_dimension(product, lang, option_label, 0)

    if group_key == 'wash_energy_class':
        return _matches_wash_energy_class(product, lang, option_label, int(option_value))

    if group_key == 'wash_spin_class':
        return _matches_field_label(product, lang, 'wash_spin_class', option_label)

    if group_key == 'wash_noise_level':
        return _matches_numeric_group(product, lang, 'wash_noise_level', option_label)

    if group_key == 'wash_water_consumption':
        return _matches_numeric_group(product, lang, 'wash_water_consumption', option_label)

    if group_key == 'wash_door_opening':
        return _matches_field_label(product, lang, 'wash_door_opening', option_label)

    if group_key == 'wash_country_of_origin':
        return _matches_field_label(product, lang, 'country_of_origin', option_label)

    return False


def _matches_microwave_group_option(product, lang, group_key, option_label, option_value):
    if group_key == 'microwave_capacity':
        return _matches_numeric_group(product, lang, 'microwave_capacity', option_label)

    if group_key == 'microwave_power':
        return _matches_numeric_group(product, lang, 'microwave_power', option_label)

    if group_key == 'microwave_features':
        return _matches_microwave_features(product, lang, option_label, int(option_value))

    if group_key == 'microwave_extra':
        return _matches_microwave_extra(product, lang, option_label, int(option_value))

    if group_key == 'microwave_controls':
        return _matches_field_label(product, lang, 'microwave_controls', option_label)

    if group_key == 'microwave_inner_coating':
        return _matches_field_label(product, lang, 'microwave_inner_coating', option_label)

    if group_key == 'microwave_door':
        return _matches_field_label(product, lang, 'microwave_door', option_label)

    if group_key == 'microwave_door_opening':
        return _matches_field_label(product, lang, 'microwave_door_opening', option_label)

    if group_key == 'microwave_release_year':
        return _matches_release_year(product, lang, int(option_value))

    if group_key == 'microwave_turntable_diameter':
        return _matches_numeric_group(product, lang, 'microwave_turntable_diameter', option_label)

    if group_key == 'microwave_height':
        return _matches_microwave_dimension(product, lang, option_label, 0)

    if group_key == 'microwave_width':
        return _matches_microwave_dimension(product, lang, option_label, 1)

    if group_key == 'microwave_depth':
        return _matches_microwave_dimension(product, lang, option_label, 2)

    return False


def _matches_numeric_group(product, lang, group_key, option_label, unit_multipliers=None):
    numeric_value = _get_numeric_value(product, lang, group_key, unit_multipliers)
    if numeric_value is None:
        return False
    return _matches_numeric_label(numeric_value, option_label, unit_multipliers)


def _matches_robot_height(product, lang, option_label):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['dimensions'].get(lang, []))
    if not dimensions:
        return False

    match = re.search(r'(\d+(?:[.,]\d+)?)', dimensions.replace(',', '.'))
    if not match:
        return False

    height_value = float(match.group(1))
    height_text = _normalize_text(dimensions)
    if 'cm' in height_text or 'см' in height_text:
        height_value *= 10

    return _matches_numeric_label(height_value, option_label)


def _matches_field_label(product, lang, field_key, option_label):
    general = _get_general_specs(product)
    field_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS[field_key].get(lang, [])))
    return _matches_text_label(field_text, option_label, lang)


def _matches_microwave_features(product, lang, option_label, option_index):
    features_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['microwave_features'].get(lang, [])))
    full_text = _get_product_text(product)
    combined_text = ' '.join(filter(None, [features_text, full_text]))

    if option_index == 0:
        return _contains_any(combined_text, ['гриль', 'grill']) and not _contains_any(combined_text, ['без гриля', 'без грилю', 'no grill'])
    if option_index == 1:
        return _contains_any(combined_text, ['без гриля', 'без грилю', 'no grill']) or not _contains_any(combined_text, ['гриль', 'grill'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_microwave_extra(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    extra_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['microwave_extra'].get(lang, [])))
    full_text = _get_product_text(product)
    combined_text = ' '.join(filter(None, [extra_text, full_text]))

    if option_index == 3:
        return (
            _contains_any(combined_text, ['поворотн', 'turntable'])
            and not _contains_any(combined_text, ['без поворот', 'без поворотного', 'без поворотного диска', 'no turntable'])
        ) or _get_numeric_value(product, lang, 'microwave_turntable_diameter') is not None
    if option_index == 4:
        return _contains_any(combined_text, ['без поворот', 'без поворотного', 'без поворотного диска', 'no turntable'])
    if option_index == 7:
        return _contains_any(combined_text, ['блокировк', 'блокуван', 'door lock'])
    if option_index == 8:
        return _matches_truthy_or_text(product, lang, 'display', ['диспле', 'display'])
    if option_index == 9:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_microwave_dimension(product, lang, option_label, index):
    dimension_value = _get_microwave_dimension_value(product, lang, index)
    if dimension_value is None:
        return False
    return _matches_numeric_label(dimension_value, option_label)


def _matches_oven_device_type(product, lang, option_index):
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['type'].get(lang, [])))

    if option_index == 0:
        return _contains_any(type_text, ['электр', 'електр', 'electric'])
    if option_index == 1:
        return _contains_any(type_text, ['газов', 'gas'])
    if option_index == 2:
        return _contains_any(type_text, ['паровар', 'steam'])
    return False


def _matches_oven_cooking_modes(product, lang, option_label, option_index):
    modes_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['oven_cooking_modes'].get(lang, [])))
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['type'].get(lang, [])))
    full_text = _get_product_text(product)
    combined_text = ' '.join(filter(None, [type_text, modes_text, full_text]))

    if option_index == 0:
        return _contains_any(combined_text, ['микровол', 'мікрохвиль', 'microwave'])
    if option_index == 1:
        return not _contains_any(combined_text, ['микровол', 'мікрохвиль', 'microwave'])
    if option_index == 2:
        return _contains_any(combined_text, ['паровар', 'built-in steamer', 'steam oven'])
    if option_index == 3:
        return _contains_any(combined_text, ['на пару', 'на парі', 'steam cooking', 'steam'])
    if option_index == 8:
        return _matches_truthy_or_text(product, lang, 'thermoprobe', ['термощуп', 'temperature probe'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_oven_section_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    features_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['oven_features_list'].get(lang, [])))
    full_text = _get_product_text(product)
    guides_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['oven_guides'].get(lang, [])))
    combined_text = ' '.join(filter(None, [features_text, guides_text, full_text]))

    if option_index == 0:
        return _contains_any(combined_text, ['таймер', 'timer'])
    if option_index == 1:
        return _contains_any(combined_text, ['автоотключ', 'автовимк', 'auto switch-off'])
    if option_index == 2:
        automatic_programs = _extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['oven_automatic_programs'].get(lang, [])))
        return (automatic_programs is not None and automatic_programs > 0) or _contains_any(combined_text, ['автоприготов', 'autocooking'])
    if option_index == 3:
        return _contains_any(combined_text, ['мобильн', 'мобільн', 'mobile app', 'wi-fi', 'wifi'])
    if option_index == 4:
        return _contains_any(combined_text, ['tft'])
    if option_index == 5:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    if option_index == 6:
        glass_count = _extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['glass_count'].get(lang, [])))
        return glass_count is not None and glass_count >= 3
    if option_index == 7:
        return _contains_any(guides_text + ' ' + combined_text, ['телескоп', 'telescop'])
    if option_index == 8:
        return _matches_truthy_or_text(product, lang, 'door_closer', ['доводчик', 'door closer', 'soft closing'])
    if option_index == 9:
        return _contains_any(combined_text, ['кнопк', 'button door opening'])
    if option_index == 10:
        return _contains_any(combined_text, ['двойн', 'подвійн', 'double oven', 'additional chamber'])
    if option_index == 11:
        return _contains_any(combined_text, ['видеокамер', 'відеокамер', 'video camera'])
    if option_index == 12:
        return _contains_any(combined_text, ['ретро', 'retro'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_oven_temperature(product, lang, option_label, mode):
    temperature_value = _get_oven_temperature_value(product, lang, mode)
    if temperature_value is None:
        return False
    return _matches_numeric_label(temperature_value, option_label)


def _matches_oven_height(product, lang, option_index):
    height = _get_cooker_dimension_value(product, lang, 0)
    if height is None:
        return False
    if option_index == 0:
        return height < 52
    if option_index == 1:
        return height >= 52
    return False


def _matches_oven_width(product, lang, option_index):
    width = _get_cooker_dimension_value(product, lang, 1)
    if width is None:
        return False
    if option_index == 0:
        return width < 52.5
    if option_index == 1:
        return 52.5 <= width < 75
    if option_index == 2:
        return width >= 75
    return False


def _matches_oven_cutout_depth(product, lang, option_label):
    depth = _get_oven_cutout_dimension_value(product, lang, 2)
    if depth is None:
        return False
    if depth > 100:
        depth /= 10
    return _matches_numeric_label(depth, option_label)


def _matches_wash_type(product, lang, option_index):
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['wash_type'].get(lang, [])))
    full_text = _get_product_text(product)
    depth = _get_wash_dimension_value(product, lang, 2)
    height = _get_wash_dimension_value(product, lang, 0)
    combined_text = ' '.join(filter(None, [type_text, full_text]))

    if option_index == 0:
        return _contains_any(type_text, ['фронт', 'front'])
    if option_index == 1:
        return _contains_any(type_text, ['вертик', 'top'])
    if option_index == 2:
        return (depth is not None and depth <= 40) or _contains_any(combined_text, ['узк', 'slim', 'narrow'])
    if option_index == 3:
        return (height is not None and height <= 80) or _contains_any(combined_text, ['компакт', 'compact'])
    if option_index == 4:
        return _contains_any(combined_text, ['полуавтомат', 'напівавтомат', 'semiautomatic'])
    if option_index == 5:
        return _contains_any(combined_text, ['2 барабан', '2 drum', 'two drums'])
    if option_index == 6:
        return _contains_any(combined_text, ['бак для воды', 'бак для води', 'water tank'])
    return False


def _matches_wash_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    display_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['display'].get(lang, [])))
    tank_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_tank_material'].get(lang, [])))
    heating_element_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_heating_element_material'].get(lang, [])))
    drum_lighting_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_drum_lighting'].get(lang, [])))
    opening_angle_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_opening_angle'].get(lang, [])))
    drying_presence_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_dryer_presence'].get(lang, [])))
    drying_capacity = _get_numeric_value(product, lang, 'wash_drying_capacity')
    full_text = _get_product_text(product)
    combined_text = ' '.join(filter(None, [display_text, tank_text, heating_element_text, drum_lighting_text, opening_angle_text, full_text]))
    explicit_has_drying = drying_presence_text in BOOLEAN_TRUE_VALUES.get(lang, BOOLEAN_TRUE_VALUES['en'])
    explicit_has_no_drying = drying_presence_text in {
        'ru': {'нет', '-', 'отсутствует'},
        'ua': {'немає', 'ні', '-', 'відсутнє', 'відсутня'},
        'en': {'no', '-', 'none', 'absent'},
    }.get(lang, {'no', '-', 'none', 'absent'})
    has_no_drying_text = _contains_any(full_text, [
        'без суш',
        'нет суш',
        'немає суш',
        'відсутн суш',
        'отсутствует суш',
        'no dryer',
        'no drying',
        'without dryer',
        'without drying',
    ])
    has_drying_text = _contains_any(full_text, [
        'стирально-суш',
        'прально-суш',
        'washer dryer',
        'wash+dry',
    ])
    has_no_drying = explicit_has_no_drying or has_no_drying_text
    has_drying = explicit_has_drying or drying_capacity is not None or (not has_no_drying and has_drying_text)

    if option_index == 0:
        return has_drying and not has_no_drying
    if option_index == 1:
        return has_no_drying or not has_drying
    if option_index == 2:
        return _matches_truthy_or_text(product, lang, 'wash_steam', ['паром', 'парою', 'steam wash'])
    if option_index == 3:
        return _contains_any(combined_text, ['пузыр', 'бульбаш', 'bubble wash'])
    if option_index == 4:
        return _matches_truthy_or_text(product, lang, 'wash_direct_injection', ['прямого впрыск', 'прямого впорск', 'direct injection'])
    if option_index == 5:
        return _matches_truthy_or_text(product, lang, 'wash_auto_dosing', ['автоматическ', 'автоматичн', 'automatic dosing'])
    if option_index == 6:
        return _contains_any(combined_text, ['струйн', 'струмин', 'jet rinse'])
    if option_index == 7:
        return _contains_any(combined_text, ['интеллект', 'інтелект', 'smart wash'])
    if option_index == 8:
        return _contains_any(combined_text, ['таймер окончания', 'таймер закінчення', 'end of cycle timer'])
    if option_index == 9:
        return _contains_any(combined_text, ['прямой привод', 'прямий привід', 'direct drive'])
    if option_index == 10:
        return _matches_truthy_or_text(product, lang, 'wash_inverter_motor', ['инвертор', 'inverter'])
    if option_index == 11:
        return _contains_any(tank_text, ['нержав', 'stainless'])
    if option_index == 12:
        return _contains_any(display_text, ['led'])
    if option_index == 13:
        return _contains_any(display_text, ['tft'])
    if option_index == 14:
        return bool(drum_lighting_text) and not _contains_any(drum_lighting_text, ['нет', 'відсут', 'no'])
    if option_index == 15:
        return _contains_any(combined_text, ['дозагруз', 'дозавантаж', 'reloading hatch'])
    if option_index == 16:
        return _contains_any(combined_text, ['иного цвета', 'іншого кольору', 'different colour'])
    if option_index == 17:
        angle = _extract_numeric_value(opening_angle_text)
        return (angle is not None and angle >= 180) or _contains_any(combined_text, ['180°', '180'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_wash_programmes(product, lang, option_label):
    programmes_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['wash_programmes'].get(lang, [])))
    return _matches_text_label(programmes_text, option_label, lang)


def _matches_wash_controls(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    controls_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_controls'].get(lang, [])))
    smartphone_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_smartphone_control'].get(lang, [])))
    combined_text = ' '.join(filter(None, [controls_text, smartphone_text, _get_product_text(product)]))

    if option_index in {0, 1, 2}:
        return _matches_text_label(controls_text, option_label, lang)
    if option_index == 3:
        return _contains_any(combined_text, ['bluetooth'])
    if option_index == 4:
        return _contains_any(combined_text, ['wi-fi', 'wifi'])
    if option_index == 5:
        return _contains_any(combined_text, ['голосов', 'voice assistant', 'alexa', 'google assistant'])
    return False


def _matches_wash_protection(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    heating_element_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_heating_element_material'].get(lang, [])))
    full_text = _get_product_text(product)

    if option_index == 0:
        return _matches_truthy_or_text(product, lang, 'wash_leak_protection', ['протеч', 'протікан', 'leak protection'])
    if option_index == 1:
        return _matches_truthy_or_text(product, lang, 'wash_imbalance_control', ['дисбаланс', 'unbalance'])
    if option_index == 2:
        return _matches_truthy_or_text(product, lang, 'wash_foam_control', ['пенообраз', 'піноутвор', 'anti-foam', 'foam control'])
    if option_index == 3:
        return _contains_any(full_text, ['перепадов напряж', 'перепадів напруг', 'surge protection'])
    if option_index == 4:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    if option_index == 5:
        return _contains_any(heating_element_text, ['керами', 'ceramic'])
    if option_index == 6:
        return _contains_any(heating_element_text, ['никел', 'нікель', 'nickel'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_wash_dimension(product, lang, option_label, index):
    dimension_value = _get_wash_dimension_value(product, lang, index)
    if dimension_value is None:
        return False
    return _matches_numeric_label(dimension_value, option_label)


def _matches_wash_energy_class(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    if option_index <= 5:
        value = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_energy_class_new'].get(lang, [])))
    else:
        value = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['wash_energy_class_old'].get(lang, [])))
    return bool(value) and _normalize_text(option_label) in value


def _matches_coffee_type(product, lang, option_index):
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['type'].get(lang, [])))
    full_text = _get_product_text(product)

    if option_index == 0:
        return _contains_any(type_text + ' ' + full_text, ['фильтрац', 'крапель', 'drip', 'filter coffee'])
    if option_index == 1:
        return _contains_any(type_text + ' ' + full_text, ['рожков', 'ріжков', 'portafilter'])
    if option_index == 2:
        return _contains_any(type_text + ' ' + full_text, ['автомат', 'automatic'])
    if option_index == 3:
        return _contains_any(type_text + ' ' + full_text, ['портатив', 'portable'])
    if option_index == 4:
        return _contains_any(type_text + ' ' + full_text, ['капсул', 'capsule'])
    if option_index == 5:
        return _contains_any(type_text + ' ' + full_text, ['комбін', 'комбин', 'combined'])
    if option_index == 6:
        return _contains_any(type_text + ' ' + full_text, ['гейзер', 'moka'])
    if option_index == 7:
        return _contains_any(type_text + ' ' + full_text, ['турк', 'turkish'])
    return False


def _matches_coffee_programs(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    programs_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['coffee_programs'].get(lang, [])))

    if option_index == 17:
        custom_program = _get_value_by_keys(general, GENERAL_KEYS['custom_program'].get(lang, []))
        return bool(custom_program) or _matches_text_label(programs_text, option_label, lang)
    if option_index == 18:
        user_profiles = _get_value_by_keys(general, GENERAL_KEYS['user_profiles'].get(lang, []))
        return bool(user_profiles) or _matches_text_label(programs_text, option_label, lang)
    return _matches_text_label(programs_text, option_label, lang)


def _matches_coffee_milk_drinks(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    milk_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['milk_drinks'].get(lang, [])))

    if option_index == 4:
        return not milk_text or _contains_any(milk_text, ['отсут', 'відсут', 'no milk'])
    return _matches_text_label(milk_text, option_label, lang)


def _matches_coffee_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)
    grinder_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['built_in_grinder'].get(lang, [])))
    hoppers_text = _get_value_by_keys(general, GENERAL_KEYS['hopper_count'].get(lang, []))
    smartphone_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['smartphone_control'].get(lang, [])))
    milk_tank_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['milk_tank'].get(lang, [])))

    if option_index == 0:
        return bool(grinder_text)
    if option_index == 1:
        return _contains_any(grinder_text, ['керами', 'ceramic'])
    if option_index == 2:
        hopper_count = _extract_numeric_value(hoppers_text)
        return hopper_count is not None and hopper_count > 1
    if option_index == 5:
        return bool(milk_tank_text) and not _contains_any(milk_tank_text, ['нет', 'відсут', 'no'])
    if option_index == 6:
        return _contains_any(full_text, ['пенк', 'пінк', 'foam'])
    if option_index == 10:
        return _contains_any(smartphone_text + ' ' + full_text, ['bluetooth'])
    if option_index == 11:
        return _contains_any(smartphone_text + ' ' + full_text, ['wi-fi', 'wifi'])
    if option_index == 12:
        return _contains_any(full_text, ['таймер', 'timer'])
    if option_index == 13:
        return _contains_any(full_text, ['диспле', 'display'])
    if option_index == 14:
        return _contains_any(full_text, ['сенсорный дисплей', 'сенсорний дисплей', 'touchscreen', 'touch screen'])
    if option_index == 15:
        return _contains_any(full_text, ['сенсорные кноп', 'сенсорні кноп', 'touch buttons'])
    if option_index == 19:
        return _contains_any(full_text, ['защита от детей', 'захист від дітей', 'child lock'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_cooker_type(product, lang, option_index):
    general = _get_general_specs(product)
    oven_type = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['oven_type'].get(lang, [])))
    full_text = _get_product_text(product)
    height = _get_cooker_dimension_value(product, lang, 0)
    is_tabletop = not oven_type and (height is None or height < 30 or _contains_any(full_text, ['настоль', 'настіль', 'tabletop']))

    if option_index == 0:
        return is_tabletop
    if option_index == 1:
        return not is_tabletop
    return False


def _matches_burner_type(product, lang, option_index):
    general = _get_general_specs(product)
    hob_type = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['hob_type'].get(lang, [])))
    counts = _get_cooker_burner_counts(product, lang)
    electric_count = counts['induction'] + counts['hilight'] + counts['halogen'] + counts['cast_iron'] + counts['spiral']
    gas_count = counts['gas']

    if option_index == 0:
        return gas_count > 0 and electric_count == 0 and not _contains_any(hob_type, ['комб', 'combined'])
    if option_index == 1:
        return electric_count > 0 and gas_count == 0
    if option_index == 2:
        return counts['induction'] > 0
    if option_index == 3:
        return counts['hilight'] > 0
    if option_index == 4:
        return counts['halogen'] > 0
    if option_index == 5:
        return counts['cast_iron'] > 0 and electric_count == counts['cast_iron']
    if option_index == 6:
        return counts['spiral'] > 0
    if option_index == 7:
        return gas_count > 0 and electric_count > 0 or _contains_any(hob_type, ['комб', 'combined'])
    if option_index == 8:
        return counts['cast_iron'] > 0
    return False


def _matches_burners_count(product, option_label):
    burners_count = _get_total_cooker_burners(product, 'ru')
    if burners_count is None:
        burners_count = _get_total_cooker_burners(product, 'ua')
    if burners_count is None:
        burners_count = _get_total_cooker_burners(product, 'en')
    if burners_count is None:
        return False
    return _matches_numeric_label(burners_count, option_label)


def _matches_cooker_burner_power(product, lang, option_label, mode):
    power_value = _get_cooker_burner_power_value(product, lang, mode)
    if power_value is None:
        return False
    return _matches_numeric_label(power_value, option_label, {('квт', 'kw'): 1, ('вт', 'w'): 0.001})


def _matches_cooker_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)

    if option_index == 0:
        return _matches_truthy_or_text(product, lang, 'gas_control', ['газ-контроль'])
    if option_index == 1:
        return _matches_truthy_or_text(product, lang, 'auto_ignition', ['автоподжиг', 'автопідпал', 'auto ignition'])
    if option_index == 2:
        return _matches_truthy_or_text(product, lang, 'auto_power_off', ['автоотключ', 'автовимк'])
    if option_index == 3:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    if option_index == 4:
        return _matches_truthy_or_text(product, lang, 'flex_zone', ['flexzone', 'flex zone'])
    if option_index == 5:
        return _matches_truthy_or_text(product, lang, 'bridge_mode', ['bridge', 'мост', 'міст'])
    if option_index == 6:
        return _matches_truthy_or_text(product, lang, 'oval_zone', ['овальн', 'oval'])
    if option_index == 7:
        return _matches_truthy_or_text(product, lang, 'contour_burner', ['контурн', 'dual-circuit'])
    if option_index == 8:
        return _get_cooker_burner_counts(product, lang)['wok'] > 0 or _contains_any(full_text, ['турбоконфор', 'turbo burner', 'wok'])
    if option_index == 9:
        return _matches_truthy_or_text(product, lang, 'residual_heat', ['остаточн', 'залишков', 'heat indicator'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_oven_features(product, lang, option_label, option_index):
    full_text = _get_product_text(product)

    if option_index == 0:
        return _matches_truthy_or_text(product, lang, 'gas_control', ['газ-контроль'])
    if option_index == 1:
        return _matches_truthy_or_text(product, lang, 'auto_ignition', ['автоподжиг', 'автопідпал', 'auto ignition'])
    if option_index == 2:
        return _matches_truthy_or_text(product, lang, 'auto_power_off', ['автоотключ', 'автовимк'])
    if option_index == 3:
        return _contains_any(full_text, ['термостат', 'thermostat'])
    if option_index == 4:
        return _contains_any(full_text, ['гриль', 'grill'])
    if option_index == 5:
        return _contains_any(full_text, ['конвекц', 'convection'])
    if option_index == 6:
        return _contains_any(full_text, ['вертел', 'рожен', 'rotisserie'])
    if option_index == 7:
        return _matches_truthy_or_text(product, lang, 'thermoprobe', ['термощуп', 'temperature probe'])
    if option_index == 8:
        return _contains_any(full_text, ['пар', 'steam'])
    if option_index == 9:
        return _contains_any(full_text, ['телескоп', 'telescopic'])
    if option_index == 10:
        return _contains_any(full_text, ['таймер', 'timer'])
    if option_index == 11:
        return _contains_any(full_text, ['дополнительная камера', 'додаткова камера', 'additional chamber'])
    if option_index == 12:
        return _contains_any(full_text, ['блокировк', 'door lock'])
    if option_index == 13:
        return _matches_truthy_or_text(product, lang, 'door_closer', ['доводчик', 'door closer'])
    if option_index == 14:
        glass_count = _extract_numeric_value(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['glass_count'].get(lang, [])))
        return glass_count is not None and glass_count >= 3
    return _matches_text_label(full_text, option_label, lang)


def _matches_release_year(product, lang, option_index):
    general = _get_general_specs(product)
    value = _get_value_by_keys(general, {
        'ru': ['Дата добавления на E-Katalog'],
        'ua': ['Дата додавання на E-Katalog'],
        'en': ['Date added to E-Katalog'],
    }.get(lang, []))
    year = _extract_last_year(value)
    if year is None:
        return False
    if option_index == 0:
        return year >= 2026
    if option_index == 1:
        return year == 2025
    if option_index == 2:
        return year < 2025
    return False


def _matches_combined_burners(product, option_index):
    counts = _get_cooker_burner_counts(product, 'ru')
    gas_count = counts['gas']
    electric_count = counts['induction'] + counts['hilight'] + counts['halogen'] + counts['cast_iron'] + counts['spiral']
    if option_index == 0:
        return gas_count == 3 and electric_count == 1
    if option_index == 1:
        return gas_count == 2 and electric_count == 2
    return False


def _matches_cooker_dimension(product, lang, option_label, index):
    dimension_value = _get_cooker_dimension_value(product, lang, index)
    if dimension_value is None:
        return False
    return _matches_numeric_label(dimension_value, option_label)


def _matches_dishwasher_format(product, lang, option_index):
    full_text = _get_product_text(product)
    height = _get_dishwasher_dimension_value(product, lang, 0)
    width = _get_dishwasher_dimension_value(product, lang, 1)
    is_compact = (
        (height is not None and height < 60)
        or _contains_any(full_text, ['компакт', 'настоль', 'настіл', 'countertop', 'tabletop'])
        or (width is not None and width <= 56 and height is not None and height < 70)
    )

    if option_index == 0:
        return is_compact
    if option_index == 1:
        return not is_compact
    return False


def _matches_dishwasher_width(product, lang, option_index):
    width = _get_dishwasher_dimension_value(product, lang, 1)
    if width is None:
        return False

    if option_index == 0:
        return width < 50
    if option_index == 1:
        return 50 <= width < 57
    if option_index == 2:
        return width >= 57
    return False


def _matches_dishwasher_programs(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    programs_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['dishwasher_programs'].get(lang, [])))

    if option_index == 7:
        return _contains_any(programs_text, ['ночн', 'тих', 'quiet', 'silent']) or _matches_text_label(programs_text, option_label, lang)
    if option_index == 9:
        return _contains_any(programs_text, ['пар', 'steam']) or _matches_text_label(programs_text, option_label, lang)
    return _matches_text_label(programs_text, option_label, lang)


def _matches_dishwasher_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)

    if option_index == 0:
        return _contains_any(full_text, ['лоток для прибор', 'лоток для прилад', 'cutlery tray', 'third rack', 'third level', 'третьим выдвижным уровнем'])
    if option_index == 1:
        value = _get_value_by_keys(general, {
            'ru': ['Дополнительные форсунки'],
            'ua': ['Додаткові форсунки'],
            'en': ['Additional nozzles'],
        }.get(lang, []))
        return bool(value) or _contains_any(full_text, ['дополнительные форсунк', 'додаткові форсунк', 'additional nozzle', 'duopower', 'cornerintense'])
    if option_index == 2:
        value = _get_value_by_keys(general, {
            'ru': ['Регулировка верхней корзины'],
            'ua': ['Регулювання верхнього кошика'],
            'en': ['Upper basket adjustment'],
        }.get(lang, []))
        return bool(value) or _contains_any(full_text, ['регулировк', 'регулюван', 'upper basket adjustment'])
    if option_index == 3:
        return bool(_get_value_by_keys(general, {
            'ru': ['Таймер отсрочки запуска'],
            'ua': ['Таймер відстрочки запуску'],
            'en': ['Delay timer'],
        }.get(lang, []))) or _contains_any(full_text, ['отложен', 'відстроч', 'delay timer'])
    if option_index == 4:
        return _matches_truthy_or_text(product, lang, 'dishwasher_hot_water_supply', ['горяч', 'гаряч', 'hot water'])
    if option_index == 5:
        return bool(_get_value_by_keys(general, GENERAL_KEYS['dishwasher_no_plumbing'].get(lang, []))) or _contains_any(
            full_text,
            ['не требуется водопровод', 'без водопровода', 'не потрібний водопровід', 'no plumbing'],
        )
    if option_index == 6:
        return bool(_get_value_by_keys(general, {
            'ru': ['Инверторный двигатель'],
            'ua': ['Інверторний двигун'],
            'en': ['Inverter motor'],
        }.get(lang, []))) or _contains_any(full_text, ['инвертор', 'інвертор', 'inverter'])
    if option_index == 7:
        return _contains_any(full_text, ['автодоводчик', 'autocloser', 'door closer'])
    if option_index == 8:
        return bool(_get_value_by_keys(general, {
            'ru': ['Автооткрывание дверцы'],
            'ua': ['Автовідкривання дверцят'],
            'en': ['Auto door opening'],
        }.get(lang, []))) or _contains_any(full_text, ['автооткрыван', 'автовідкрив', 'auto door opening'])
    if option_index == 9:
        return bool(_get_value_by_keys(general, {
            'ru': ['Управление со смартфона (Wi-Fi)', 'Управление через Интернет'],
            'ua': ['Управління зі смартфона (Wi-Fi)', 'Керування через Інтернет'],
            'en': ['Control from smartphone (Wi-Fi)', 'Control via internet'],
        }.get(lang, []))) or _contains_any(full_text, ['wi-fi', 'wifi', 'интернет', 'internet'])
    if option_index == 10:
        return bool(_get_value_by_keys(general, {
            'ru': ['Дисплей'],
            'ua': ['Дисплей'],
            'en': ['Display'],
        }.get(lang, []))) or _contains_any(full_text, ['диспле', 'display'])
    if option_index == 11:
        return _contains_any(full_text, ['tft'])
    if option_index == 12:
        return _matches_truthy_or_text(product, lang, 'dishwasher_end_signal', ['сигнал окончания', 'сигнал закінчення', 'end-of-cycle signal'])
    if option_index == 13:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    if option_index == 14:
        return _contains_any(full_text, ['подсветк', 'підсвічуван', 'interior lighting'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_dishwasher_energy_class(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    if option_index in {0, 1, 2, 4, 6}:
        current_value = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['dishwasher_energy_class_new'].get(lang, [])))
    else:
        current_value = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['energy_class'].get(lang, [])))

    if not current_value:
        return False

    if option_index == 0:
        return current_value.startswith('b')
    if option_index == 1:
        return current_value.startswith('c')
    if option_index == 2:
        return current_value.startswith('d')
    if option_index == 3:
        return 'a+++' in current_value
    if option_index == 4:
        return current_value.startswith('e')
    if option_index == 5:
        return 'a++' in current_value and 'a+++' not in current_value
    if option_index == 6:
        return current_value.startswith('f')
    if option_index == 7:
        return 'a+' in current_value and 'a++' not in current_value
    return _matches_text_label(current_value, option_label, lang)


def _matches_fridge_type(product, lang, option_index):
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['type'].get(lang, [])))
    full_text = _get_product_text(product)
    combined_text = f'{type_text} {full_text}'

    if option_index == 0:
        return not _contains_any(combined_text, ['side-by-side', 'side by side', 'french-door', 'french door', 'витрин', 'vitrina', 'display refrigerator'])
    if option_index == 1:
        return _contains_any(combined_text, ['side-by-side', 'side by side'])
    if option_index == 2:
        return _contains_any(combined_text, ['french-door', 'french door'])
    if option_index == 3:
        return _contains_any(combined_text, ['витрин', 'display refrigerator'])
    return False


def _matches_fridge_chambers(product, lang, option_index):
    chambers_count = _get_numeric_value(product, lang, 'fridge_chambers')
    if chambers_count is None:
        return False

    if option_index == 0:
        return chambers_count == 1
    if option_index == 1:
        return chambers_count == 2
    if option_index == 2:
        return chambers_count == 3
    if option_index == 3:
        return chambers_count >= 4
    return False


def _matches_fridge_freezer_position(product, lang, option_index):
    freezer_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['fridge_freezer_position'].get(lang, [])))

    if option_index == 0:
        return _contains_any(freezer_text, ['сверх', 'зверх', 'top'])
    if option_index == 1:
        return _contains_any(freezer_text, ['сниз', 'зниз', 'bottom']) and not _contains_any(freezer_text, ['выдв', 'висув', 'retract'])
    if option_index == 2:
        return _contains_any(freezer_text, ['выдв', 'висув', 'retract'])
    if option_index == 3:
        return _contains_any(freezer_text, ['сбок', 'збок', 'side'])
    if option_index == 4:
        return _contains_any(freezer_text, ['отсутств', 'відсут', 'no freezer'])
    return False


def _matches_fridge_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)
    no_frost_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['fridge_no_frost'].get(lang, [])))
    freeze_temperature = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['freeze_temperature'].get(lang, [])))
    cooling_circuits = _get_numeric_value(product, lang, 'cooling_circuits')
    compressors = _get_numeric_value(product, lang, 'compressors')
    freeze_power = _get_numeric_value(product, lang, 'freeze_power')
    has_full_no_frost = (
        _contains_any(no_frost_text, ['холодиль', 'refrigerator'])
        and _contains_any(no_frost_text, ['морозил', 'freezer'])
    ) or _contains_any(full_text, ['полностью no frost', 'повністю no frost', 'full no frost'])

    if option_index == 0:
        return has_full_no_frost
    if option_index == 1:
        return not has_full_no_frost and _contains_any(no_frost_text, ['морозил', 'freezer'])
    if option_index == 2:
        return not no_frost_text or _contains_any(full_text, ['без no frost', 'without no frost', 'self-defrosting', 'капельн', 'крапельн'])
    if option_index == 3:
        return _contains_any(full_text, ['инвертор', 'інвертор', 'inverter'])
    if option_index == 4:
        return _matches_truthy_or_text(product, lang, 'fast_freeze', ['быстрая заморозка', 'швидка заморозка', 'fast freeze'])
    if option_index == 5:
        return _matches_truthy_or_text(product, lang, 'fast_cool', ['быстрое охлаждение', 'швидке охолодження', 'fast cool'])
    if option_index == 6:
        return _matches_truthy_or_text(product, lang, 'dynamic_cooling', ['динамическое охлаждение', 'динамічне охолодження', 'dynamic air cooling'])
    if option_index == 7:
        return freeze_power is not None and freeze_power >= 10
    if option_index == 8:
        return _contains_any(freeze_temperature, ['24']) or _contains_any(full_text, ['-24', '−24'])
    if option_index == 9:
        return _contains_any(full_text, ['режим отпуска', 'режим відпустки', 'holiday mode'])
    if option_index == 10:
        return _contains_any(full_text, ['дезодоратор', 'deodorizer'])
    if option_index == 11:
        return cooling_circuits is not None and cooling_circuits >= 2
    if option_index == 12:
        return compressors is not None and compressors >= 2
    return _matches_text_label(full_text, option_label, lang)


def _matches_fridge_compartments(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)
    storage_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['fridge_storage'].get(lang, [])))
    water_dispenser_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['water_dispenser'].get(lang, [])))
    ice_maker_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['ice_maker'].get(lang, [])))
    combined_text = ' '.join(filter(None, [storage_text, water_dispenser_text, ice_maker_text, full_text]))

    if option_index == 7:
        return bool(water_dispenser_text) or _contains_any(combined_text, ['диспенсер', 'water dispenser'])
    if option_index == 8:
        return bool(ice_maker_text) or _contains_any(combined_text, ['ледогенерат', 'льодогенерат', 'ice maker'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_fridge_additional(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)
    functions_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['fridge_functions'].get(lang, [])))
    additional_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['fridge_additional'].get(lang, [])))
    combined_text = ' '.join(filter(None, [functions_text, additional_text, full_text]))

    if option_index == 8:
        return _contains_any(combined_text, ['led освещ', 'led lighting', 'led light', 'led освітл'])
    if option_index == 9:
        return _contains_any(combined_text, ['led диспл', 'led display'])
    if option_index == 10:
        return _contains_any(combined_text, ['tft'])
    if option_index == 11:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    if option_index == 13:
        return _contains_any(combined_text, ['управление со смартфона', 'керування зі смартфона', 'wi-fi', 'wifi', 'control via internet'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_fridge_height(product, lang, option_index):
    height = _get_fridge_dimension_value(product, lang, 0)
    if height is None:
        return False

    ranges = [
        (None, 85),
        (86, 100),
        (101, 125),
        (126, 150),
        (151, 170),
        (171, 180),
        (181, 190),
        (191, 200),
    ]
    if option_index < len(ranges):
        lower, upper = ranges[option_index]
        if lower is None:
            return height <= upper
        return lower <= height <= upper
    if option_index == 8:
        return height > 200
    return False


def _matches_fridge_width(product, lang, option_index):
    width = _get_fridge_dimension_value(product, lang, 1)
    if width is None:
        return False

    ranges = [
        (None, 47.5),
        (47.5, 52.5),
        (52.5, 57.5),
        (57.5, 62.5),
        (62.5, 67.5),
        (67.5, 72.5),
        (72.5, 77.5),
        (77.5, 82.5),
        (82.5, 87.5),
        (87.5, 105),
    ]
    if option_index < len(ranges):
        lower, upper = ranges[option_index]
        if lower is None:
            return width < upper
        return lower <= width < upper
    if option_index == 10:
        return width >= 105
    return False


def _matches_fridge_energy_class(product, lang, option_index):
    general = _get_general_specs(product)
    if option_index <= 5:
        current_value = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['fridge_energy_class_new'].get(lang, [])))
    else:
        current_value = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['energy_class'].get(lang, [])))

    if not current_value:
        return False

    if option_index == 0:
        return current_value.startswith('a')
    if option_index == 1:
        return current_value.startswith('b')
    if option_index == 2:
        return current_value.startswith('c')
    if option_index == 3:
        return current_value.startswith('d')
    if option_index == 4:
        return current_value.startswith('e')
    if option_index == 5:
        return current_value.startswith('f')
    if option_index == 6:
        return 'a+++' in current_value
    if option_index == 7:
        return 'a++' in current_value and 'a+++' not in current_value
    if option_index == 8:
        return 'a+' in current_value and 'a++' not in current_value
    return False


def _matches_fridge_freezer_drawers(product, lang, option_label):
    drawers_count = _get_fridge_freezer_drawers_count(product, lang)
    if drawers_count is None:
        return False
    return _matches_numeric_label(drawers_count, option_label)


def _matches_fridge_depth(product, lang, option_index):
    depth = _get_fridge_dimension_value(product, lang, 2)
    if depth is None:
        return False

    ranges = [
        (None, 47.5),
        (47.5, 52.5),
        (52.5, 57.5),
        (57.5, 62.5),
        (62.5, 67.5),
        (67.5, 72.5),
        (72.5, 77.5),
    ]
    if option_index < len(ranges):
        lower, upper = ranges[option_index]
        if lower is None:
            return depth < upper
        return lower <= depth < upper
    if option_index == 7:
        return depth >= 77.5
    return False


def _matches_hob_device(product, lang, option_index):
    device_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['hob_device'].get(lang, [])))
    full_text = _get_product_text(product)
    combined_text = f'{device_text} {full_text}'

    if option_index == 0:
        return _contains_any(combined_text, ['вароч', 'вариль', 'hob', 'cooktop']) and not _contains_any(
            combined_text,
            ['гриль', 'grill', 'вок', 'wok', 'фритюр', 'fryer', 'теппан', 'teppan'],
        )
    if option_index == 1:
        return _contains_any(combined_text, ['гриль', 'grill'])
    if option_index == 2:
        return _contains_any(combined_text, ['вок', 'wok'])
    if option_index == 3:
        return _contains_any(combined_text, ['фритюр', 'fryer'])
    if option_index == 4:
        return _contains_any(combined_text, ['теппан', 'teppan'])
    return False


def _matches_hob_burner_type(product, lang, option_index):
    general = _get_general_specs(product)
    hob_type = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['hob_type'].get(lang, [])))
    counts = _get_cooker_burner_counts(product, lang)
    electric_count = counts['induction'] + counts['hilight'] + counts['halogen'] + counts['cast_iron'] + counts['spiral']
    gas_count = counts['gas']

    if option_index == 0:
        return gas_count > 0 and electric_count == 0 and not _contains_any(hob_type, ['комб', 'combined'])
    if option_index == 1:
        return electric_count > 0 and gas_count == 0
    if option_index == 2:
        return counts['induction'] > 0 and electric_count == counts['induction']
    if option_index == 3:
        return counts['hilight'] > 0 and electric_count == counts['hilight']
    if option_index == 4:
        return counts['cast_iron'] > 0 and electric_count == counts['cast_iron']
    if option_index == 5:
        return gas_count > 0 and electric_count > 0 or _contains_any(hob_type, ['комб', 'combined'])
    return False


def _matches_hob_design(product, lang, option_index):
    full_text = _get_product_text(product)
    width = _get_hob_dimension_value(product, lang, 'hob_dimensions_wd', 0)
    is_domino = (width is not None and width <= 40) or _contains_any(full_text, ['домино', 'domino'])

    if option_index == 0:
        return not is_domino and not _contains_any(full_text, ['ромб', 'diamond', 'нестандарт', 'unusual', 'ретро', 'retro'])
    if option_index == 1:
        return is_domino
    if option_index == 2:
        return _contains_any(full_text, ['ромб', 'diamond'])
    if option_index == 3:
        return _contains_any(full_text, ['нестандарт', 'unusual', 'asymmetric', 'асимметр'])
    if option_index == 4:
        return _contains_any(full_text, ['ретро', 'retro'])
    return False


def _matches_hob_controls(product, lang, option_index):
    control_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['hob_controls'].get(lang, [])))
    full_text = _get_product_text(product)
    combined_text = f'{control_text} {full_text}'

    if option_index == 0:
        return _contains_any(combined_text, ['смартфон', 'smartphone', 'wi-fi', 'wifi', 'app'])
    if option_index == 1:
        return _contains_any(combined_text, ['отдельн', 'окрем', 'separate controls'])
    if option_index == 2:
        return _contains_any(combined_text, ['поворот', 'rotary', 'knob'])
    if option_index == 3:
        return _contains_any(combined_text, ['сенсорн', 'touch']) and not _contains_any(combined_text, ['слайдер', 'slider'])
    if option_index == 4:
        return _contains_any(combined_text, ['слайдер', 'slider'])
    if option_index == 5:
        return _contains_any(combined_text, ['сбок', 'side'])
    return False


def _matches_hob_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)
    power_levels = _get_numeric_value(product, lang, 'hob_power_levels')

    if option_index == 0:
        return _contains_any(full_text, ['сплошн', 'суцільн', 'zoneless'])
    if option_index == 1:
        return _matches_truthy_or_text(product, lang, 'flex_zone', ['flexzone', 'flex zone'])
    if option_index == 2:
        return _matches_truthy_or_text(product, lang, 'bridge_mode', ['bridge', 'мост', 'міст'])
    if option_index == 3:
        return _matches_truthy_or_text(product, lang, 'oval_zone', ['овальн', 'oval'])
    if option_index == 4:
        return _matches_truthy_or_text(product, lang, 'contour_burner', ['контурн', 'dual-circuit'])
    if option_index == 5:
        return power_levels is not None and power_levels > 9
    if option_index == 6:
        return _get_cooker_burner_counts(product, lang)['wok'] > 0 or _contains_any(full_text, ['турбоконфор', 'turbo burner', 'wok'])
    if option_index == 7:
        return _matches_truthy_or_text(product, lang, 'thermoprobe', ['термощуп', 'temperature probe'])
    if option_index == 8:
        return _matches_truthy_or_text(product, lang, 'gas_control', ['газ-контроль'])
    if option_index == 9:
        return _matches_truthy_or_text(product, lang, 'auto_ignition', ['автоподжиг', 'автопідпал', 'auto ignition'])
    if option_index == 10:
        return _matches_truthy_or_text(product, lang, 'auto_power_off', ['автоотключ', 'автовимк', 'auto switch-off'])
    if option_index == 11:
        return _contains_any(full_text, ['автожар', 'auto fry'])
    if option_index == 12:
        return _contains_any(full_text, ['растаплив', 'розтопл', 'melting'])
    if option_index == 13:
        return _contains_any(full_text, ['поддержан', 'підтрим', 'keep warm'])
    if option_index == 14:
        return _contains_any(full_text, ['закипан', 'boil detection'])
    if option_index == 15:
        return _contains_any(full_text, ['пауза', 'pause'])
    if option_index == 16:
        return _contains_any(full_text, ['таймер', 'timer'])
    if option_index == 17:
        return _matches_truthy_or_text(product, lang, 'residual_heat', ['остаточн', 'залишков', 'heat indicator'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_hob_extra(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)
    display_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['display'].get(lang, [])))
    combined_text = f'{display_text} {full_text}'

    if option_index == 0:
        return _contains_any(combined_text, ['подставка', 'підставка', 'wok stand'])
    if option_index == 1:
        return bool(display_text) or _contains_any(combined_text, ['диспле', 'display'])
    if option_index == 2:
        return _matches_truthy_or_text(product, lang, 'child_lock', ['защита от детей', 'захист від дітей', 'child lock'])
    if option_index == 3:
        return _contains_any(combined_text, ['встроенн', 'вбудован', 'built-in hood'])
    if option_index == 4:
        return _contains_any(combined_text, ['управление вытяжкой', 'керування витяжкою', 'hob2hood', 'hood control'])
    if option_index == 5:
        return _contains_any(combined_text, ['ограничен', 'обмежен', 'power limit'])
    return _matches_text_label(combined_text, option_label, lang)


def _matches_hob_includes_burners(product, lang, option_index):
    counts = _get_cooker_burner_counts(product, lang)

    if option_index == 0:
        return counts['gas'] > 0
    if option_index == 1:
        return counts['induction'] > 0
    if option_index == 2:
        return counts['hilight'] > 0
    if option_index == 3:
        return counts['cast_iron'] > 0
    return False


def _matches_hob_combined_burners(product, lang, option_index):
    counts = _get_cooker_burner_counts(product, lang)
    gas_count = counts['gas']
    electric_count = counts['induction'] + counts['hilight'] + counts['halogen'] + counts['cast_iron'] + counts['spiral']

    if option_index == 0:
        return gas_count == 3 and electric_count == 1
    if option_index == 1:
        return gas_count == 2 and electric_count == 2
    return False


def _matches_hob_dimension_bucket(product, lang, field_key, index, option_index):
    value = _get_hob_dimension_value(product, lang, field_key, index)
    if value is None:
        return False

    if field_key == 'hob_dimensions_wd' and index == 0:
        boundaries = [32.5, 37.5, 42.5, 50, 57.5, 62.5, 67.5, 72.5, 77.5, 82.5, 87.5, 95]
        return _matches_range_bucket(value, option_index, boundaries)
    if field_key == 'hob_dimensions_wd' and index == 1:
        boundaries = [49, 52.5, 57.5]
        return _matches_range_bucket(value, option_index, boundaries)
    if field_key == 'hob_cutout_wd' and index == 0:
        boundaries = [547.5, 552.5, 557.5, 560.5]
        return _matches_range_bucket(value, option_index, boundaries)
    if field_key == 'hob_cutout_wd' and index == 1:
        boundaries = [482.5, 487.5, 492.5, 497.5]
        return _matches_range_bucket(value, option_index, boundaries)
    return False


def _matches_hob_frame(product, lang, option_index):
    frame_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['frame'].get(lang, [])))
    if not frame_text:
        return False

    if option_index == 0:
        return not _contains_any(frame_text, ['отсут', 'відсут', 'no frame'])
    if option_index == 1:
        return _contains_any(frame_text, ['отсут', 'відсут', 'no frame'])
    return False


def _matches_truthy_or_text(product, lang, field_key, fragments):
    general = _get_general_specs(product)
    value = _get_value_by_keys(general, GENERAL_KEYS[field_key].get(lang, []))
    if value:
        normalized_value = _normalize_text(value)
        if normalized_value in BOOLEAN_TRUE_VALUES.get(lang, BOOLEAN_TRUE_VALUES['en']):
            return True
        if _contains_any(normalized_value, fragments):
            return True
    return _contains_any(_get_product_text(product), fragments)


def _get_cooker_burner_counts(product, lang):
    general = _get_general_specs(product)
    return {
        'gas': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['gas_burners'].get(lang, []))) or 0),
        'induction': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['induction_burners'].get(lang, []))) or 0),
        'hilight': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['hilight_burners'].get(lang, []))) or 0),
        'halogen': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['halogen_burners'].get(lang, []))) or 0),
        'cast_iron': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['cast_iron_burners'].get(lang, []))) or 0),
        'spiral': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['spiral_burners'].get(lang, []))) or 0),
        'wok': int(_extract_numeric_value(_get_value_by_keys(general, GENERAL_KEYS['wok_burners'].get(lang, []))) or 0),
    }


def _get_total_cooker_burners(product, lang):
    counts = _get_cooker_burner_counts(product, lang)
    total = counts['gas'] + counts['induction'] + counts['hilight'] + counts['halogen'] + counts['cast_iron'] + counts['spiral']
    return total or None


def _get_cooker_burner_power_value(product, lang, mode):
    general = _get_general_specs(product)
    powers = _extract_all_numeric_values(
        _get_value_by_keys(general, GENERAL_KEYS['burners_power'].get(lang, [])),
        {('квт', 'kw'): 1, ('вт', 'w'): 0.001},
    )
    if not powers:
        return None
    return min(powers) if mode == 'min' else max(powers)


def _get_cooker_dimension_value(product, lang, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['dimensions_hwd'].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_dishwasher_dimension_value(product, lang, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['dimensions_hwd'].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_fridge_dimension_value(product, lang, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['dimensions_hwd'].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_hob_dimension_value(product, lang, field_key, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS[field_key].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_microwave_dimension_value(product, lang, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['dimensions_hwd'].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_oven_temperature_value(product, lang, mode):
    general = _get_general_specs(product)
    temperature_text = _get_value_by_keys(general, GENERAL_KEYS['oven_temperature'].get(lang, []))
    values = _extract_dimensions_values(temperature_text)
    if not values:
        return None
    return min(values) if mode == 'min' else max(values)


def _get_oven_cutout_dimension_value(product, lang, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['oven_cutout_hwd'].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_wash_dimension_value(product, lang, index):
    general = _get_general_specs(product)
    dimensions = _get_value_by_keys(general, GENERAL_KEYS['wash_dimensions_hwd'].get(lang, []))
    if not dimensions:
        return None
    values = _extract_dimensions_values(dimensions)
    if len(values) <= index:
        return None
    return values[index]


def _get_fridge_freezer_drawers_count(product, lang):
    general = _get_general_specs(product)
    drawers_text = _get_value_by_keys(general, GENERAL_KEYS['freezer_drawers'].get(lang, []))
    normalized_text = _normalize_text(drawers_text)
    if not normalized_text:
        return None

    drawer_patterns = {
        'ru': r'(\d+)\s*ящ',
        'ua': r'(\d+)\s*ящ',
        'en': r'(\d+)\s*draw',
    }
    drawer_match = re.search(drawer_patterns.get(lang, drawer_patterns['en']), normalized_text)
    if drawer_match:
        return int(drawer_match.group(1))

    fallback_value = _extract_numeric_value(drawers_text)
    if fallback_value is None:
        return None
    return int(fallback_value)


def _matches_range_bucket(value, option_index, boundaries):
    if option_index == 0:
        return value < boundaries[0]
    if option_index == len(boundaries):
        return value >= boundaries[-1]
    if 0 < option_index < len(boundaries):
        return boundaries[option_index - 1] <= value < boundaries[option_index]
    return False


def _extract_dimensions_values(value):
    if not value:
        return []
    return [float(number) for number in re.findall(r'\d+(?:[.,]\d+)?', str(value).replace(',', '.'))]


def _extract_all_numeric_values(value, unit_multipliers=None):
    if not value:
        return []
    multiplier = _get_unit_multiplier(str(value), unit_multipliers)
    return [
        float(number) * multiplier
        for number in re.findall(r'\d+(?:[.,]\d+)?', str(value).replace(',', '.'))
    ]


def _extract_last_year(value):
    if not value:
        return None
    matches = re.findall(r'(20\d{2})', str(value))
    if not matches:
        return None
    return int(matches[-1])


def _matches_vacuum_type(product, lang, option_index):
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['type'].get(lang, [])))
    full_text = _get_product_text(product)

    if option_index == 0:
        return _contains_any(type_text, ['обыч', 'звич', 'convent'])
    if option_index == 1:
        return _contains_any(type_text, ['робот', 'robot'])
    if option_index == 2:
        return _contains_any(type_text, ['робот', 'robot']) and _contains_any(full_text, ['док станц', 'self empty', 'самооч', 'пилесборник станции'])
    if option_index == 3:
        return _contains_any(type_text, ['вертик', 'upright'])
    if option_index == 4:
        return _contains_any(type_text + ' ' + full_text, ['вертик', 'upright']) and _contains_any(full_text, ['портатив', 'handheld'])
    if option_index == 5:
        return _contains_any(type_text + ' ' + full_text, ['автомоб', 'car'])
    if option_index == 6:
        return _contains_any(type_text + ' ' + full_text, ['ручн', 'handheld']) and not _contains_any(full_text, ['постел', 'mattress', 'bed', 'автомоб', 'car'])
    if option_index == 7:
        return _contains_any(type_text + ' ' + full_text, ['ручн', 'handheld']) and _contains_any(full_text, ['постел', 'матрас', 'bed', 'mattress'])
    if option_index == 8:
        return _contains_any(type_text + ' ' + full_text, ['хозяй', 'workshop'])
    if option_index == 9:
        return _contains_any(type_text + ' ' + full_text, ['промыш', 'строит', 'industr', 'construct'])
    if option_index == 10:
        return _contains_any(type_text + ' ' + full_text, ['точеч', 'spot'])
    if option_index == 11:
        return _contains_any(type_text + ' ' + full_text, ['ранцев', 'backpack'])
    if option_index == 12:
        return _contains_any(type_text + ' ' + full_text, ['камин', 'fireplace'])
    if option_index == 13:
        return _contains_any(type_text + ' ' + full_text, ['электровен', 'електровіник', 'electric broom'])
    return False


def _matches_floor_washing(product, lang, option_index):
    type_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['type'].get(lang, [])))
    cleaning_text = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['cleaning'].get(lang, [])))
    full_text = _get_product_text(product)

    if option_index == 0:
        return _contains_any(type_text + ' ' + full_text, ['моющ', 'миюч', 'washing'])
    if option_index == 1:
        return _contains_any(type_text, ['робот', 'robot']) and _contains_any(cleaning_text + ' ' + full_text, ['влаж', 'волог', 'wet', 'mop'])
    if option_index == 2:
        return _contains_any(type_text + ' ' + full_text, ['электрошвабр', 'електрошвабр', 'electric mop'])
    return False


def _matches_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)

    if option_index == 0:
        return _matches_truthy_key(general, lang, {
            'ru': ['Док-станция с пылесборником'],
            'ua': ['Док-станція з пилозбірником'],
            'en': ['Self emptying docking station', 'Docking station with dust collector'],
        })
    if option_index == 4:
        return _matches_truthy_key(general, lang, {
            'ru': ['Регулировка мощности'],
            'ua': ['Регулювання потужності'],
            'en': ['Power adjustment'],
        })
    if option_index == 5:
        return _contains_any(full_text, ['на ручк', 'на ручці', 'on handle'])
    if option_index == 7:
        return _matches_truthy_key(general, lang, {
            'ru': ['Подключение к смартфону'],
            'ua': ['Підключення до смартфону'],
            'en': ['Smartphone connection'],
        })
    if option_index == 10:
        return _contains_any(full_text, ['hepa'])
    if option_index == 11:
        return _contains_any(full_text, ['hepa 13', 'hepa13'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_nozzles(product, lang, option_label):
    general = _get_general_specs(product)
    nozzle_text = _normalize_text(_get_value_by_keys(general, GENERAL_KEYS['nozzles'].get(lang, [])))
    return _matches_text_label(nozzle_text, option_label, lang)


def _matches_robot_features(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    robot_text = _normalize_text(' '.join(
        value for value in (
            _get_value_by_keys(general, GENERAL_KEYS['robot_features'].get(lang, [])),
            _get_value_by_keys(general, GENERAL_KEYS['type'].get(lang, [])),
        )
        if value
    ))

    if option_index == 2:
        return _contains_any(robot_text, ['лидар', 'лазер', 'laser', 'rangefinder'])
    if option_index == 3:
        return _contains_any(robot_text, ['виртуаль', 'віртуаль', 'virtual wall', 'огранич'])
    return _matches_text_label(robot_text, option_label, lang)


def _matches_extra(product, lang, option_label, option_index):
    general = _get_general_specs(product)
    full_text = _get_product_text(product)

    if option_index == 0:
        return _contains_any(_normalize_text(_get_value_by_keys(general, {
            'ru': ['Тип трубы'],
            'ua': ['Тип трубки'],
            'en': ['Tube type'],
        }.get(lang, []))), ['телескоп', 'telescop'])
    if option_index == 6:
        return _matches_truthy_key(general, lang, {
            'ru': ['Зарядная станция'],
            'ua': ['Зарядна станція'],
            'en': ['Charging station'],
        })
    if option_index == 7:
        return _matches_truthy_key(general, lang, {
            'ru': ['Встроенная розетка'],
            'ua': ['Вбудована розетка'],
            'en': ['Built-in socket'],
        })
    if option_index == 8:
        return _contains_any(full_text, ['автомат', 'автозмот', 'automatic cord rewind', 'power cord rewind'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_battery(product, lang, option_label, option_index):
    full_text = _get_product_text(product)
    power_source = _normalize_text(_get_value_by_keys(_get_general_specs(product), GENERAL_KEYS['power_source'].get(lang, [])))

    if option_index == 2:
        return _contains_any(power_source, ['сеть', 'мереж', 'mains'])
    if option_index == 3:
        return _contains_any(full_text, ['в комплекте', 'у комплекті', 'included'])
    return _matches_text_label(full_text, option_label, lang)


def _matches_robot_shape(product, lang, option_label):
    return _matches_text_label(_get_product_text(product), option_label, lang)


def _matches_truthy_key(general, lang, key_map):
    value = _get_value_by_keys(general, key_map.get(lang, []))
    if not value:
        return False
    return _normalize_text(value) in BOOLEAN_TRUE_VALUES.get(lang, BOOLEAN_TRUE_VALUES['en'])


def _get_numeric_value(product, lang, group_key, unit_multipliers=None):
    general = _get_general_specs(product)
    value = _get_value_by_keys(general, GENERAL_KEYS[group_key].get(lang, []))
    if not value:
        return None
    return _extract_numeric_value(value, unit_multipliers)


def _extract_numeric_value(value, unit_multipliers=None):
    if not value:
        return None
    number_match = re.search(r'(\d+(?:[.,]\d+)?)', str(value).replace(',', '.'))
    if not number_match:
        return None
    multiplier = _get_unit_multiplier(str(value), unit_multipliers)
    return float(number_match.group(1)) * multiplier


def _get_unit_multiplier(value, unit_multipliers):
    if not unit_multipliers:
        return 1
    normalized_value = _normalize_text(value)
    for units, multiplier in unit_multipliers.items():
        if any(unit in normalized_value for unit in units):
            return multiplier
    return 1


def _matches_numeric_label(number, label, unit_multipliers=None):
    normalized_label = label.replace('–', '-').replace('—', '-').replace(',', '.')
    multiplier = _get_unit_multiplier(normalized_label, unit_multipliers)
    range_match = [
        float(value) * multiplier
        for value in re.findall(r'\d+(?:\.\d+)?', normalized_label)
    ]
    if normalized_label.startswith('<') and range_match:
        return number < range_match[0]
    if normalized_label.startswith('≤') and range_match:
        return number <= range_match[0]
    if normalized_label.startswith('>') and range_match:
        return number > range_match[0]
    if normalized_label.startswith('≥') and range_match:
        return number >= range_match[0]
    if len(range_match) >= 2:
        return range_match[0] <= number <= range_match[1]
    if len(range_match) == 1:
        return number == range_match[0]
    return False


def _matches_text_label(text, label, lang):
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return False

    normalized_label = _normalize_text(label)
    if normalized_label and normalized_label in normalized_text:
        return True

    label_stems = _get_label_stems(label, lang)
    if not label_stems:
        return False

    matched_stems = sum(1 for stem in label_stems if stem in normalized_text)
    required_matches = 1 if len(label_stems) == 1 else min(2, len(label_stems))
    return matched_stems >= required_matches


def _get_label_stems(label, lang):
    words = re.findall(r'[a-zA-Zа-яА-ЯіІїЇєЄ0-9]+', label.lower())
    stop_words = MATCH_STOP_WORDS.get(lang, set())
    stems = []
    for word in words:
        if word in stop_words:
            continue
        if len(word) <= 2:
            continue
        if word.isdigit():
            continue
        stems.append(word[:5])
    return stems


def _contains_any(text, fragments):
    return any(fragment in text for fragment in fragments)


def _get_product_text(product):
    general = _get_general_specs(product)
    general_text = ' '.join(f'{key} {value}' for key, value in general.items())
    return _normalize_text(' '.join(filter(None, [product.name, product.description, general_text])))


def _get_general_specs(product):
    general = product.specs.get('general') if isinstance(product.specs, dict) else {}
    return general or {}


def _get_value_by_keys(general, keys):
    for key in keys:
        value = general.get(key)
        if value:
            return str(value)
    return ''


def _normalize_text(value):
    return str(value or '').replace('ё', 'е').replace('’', "'").lower()


def build_brand_choices(brands, selected_brands):
    selected = set(selected_brands)
    return [
        {
            **brand,
            'selected': brand['slug'] in selected,
        }
        for brand in brands
    ]


def get_query_string_without_page(query_dict):
    params = query_dict.copy()
    if 'page' in params:
        del params['page']
    return params.urlencode()


def build_filter_state(groups, request_get):
    return {
        group['param']: request_get.getlist(group['param'])
        for group in groups
    }


def get_brand_slug(brand_name):
    return slugify(brand_name) or 'no-brand'
