from unittest.mock import patch
from io import StringIO
from types import SimpleNamespace

from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.test import SimpleTestCase, TestCase

from fix_washing_no_dry_from_ek import extract_drying_flag_from_html, repair_payload, specs_need_page_check, update_drying_fields

from . import brand_utils
from . import views
from .admin import BreakdownGroupAdminForm, ProductAdminForm
from .duplicate_utils import collect_product_duplicates
from .models import Breakdown, BreakdownGroup, Category, Product, VacuumBrand


class VacuumBrandUtilsTests(SimpleTestCase):
    def tearDown(self):
        brand_utils.load_vacuum_brand_lookup.cache_clear()

    @patch('catalog.brand_utils.load_vacuum_brand_names', return_value=('FRS Austria', 'iBoto', 'Idrobasa', 'Evolvo'))
    def test_alias_brand_matching_uses_canonical_names(self, _):
        brand_utils.load_vacuum_brand_lookup.cache_clear()

        self.assertEqual(
            brand_utils.find_vacuum_brand_name(
                'first_austria_fa_5541_3',
                ['FIRST Austria FA 5541-3'],
            ),
            'FIRST Austria',
        )
        self.assertEqual(
            brand_utils.find_vacuum_brand_name(
                'iclebo_omega',
                ['iClebo Omega'],
            ),
            'iClebo',
        )
        self.assertEqual(
            brand_utils.find_vacuum_brand_name(
                'idrobase_pulito_4',
                ['Idrobase Pulito 4'],
            ),
            'Idrobase',
        )
        self.assertEqual(
            brand_utils.find_vacuum_brand_name(
                'evolveo_robotrex_h6',
                ['Evolveo RoboTrex H6'],
            ),
            'Evolveo',
        )

    @patch('catalog.brand_utils.load_vacuum_brand_names', return_value=())
    def test_fallback_brand_uses_product_name_casing(self, _):
        brand_utils.load_vacuum_brand_lookup.cache_clear()

        self.assertEqual(
            brand_utils.find_vacuum_brand_name(
                'arnica_bora_3000',
                ['Arnica Bora 3000'],
            ),
            'Arnica',
        )
        self.assertEqual(
            brand_utils.find_vacuum_brand_name(
                'hoto_qwcxj001',
                ['HOTO QWCXJ001'],
            ),
            'HOTO',
        )


class FixWashingNoDryFromEkTests(SimpleTestCase):
    def test_update_drying_fields_marks_no_dry_and_removes_capacity(self):
        specs = {
            'general': {
                'Сушилка': 'да',
                'Загрузка для сушки': '5 кг',
                'Загрузка': '8 кг',
            }
        }

        fixed = update_drying_fields(specs, 'ru')

        self.assertEqual(fixed['general']['Сушилка'], 'нет')
        self.assertNotIn('Загрузка для сушки', fixed['general'])
        self.assertEqual(fixed['general']['Загрузка'], '8 кг')

    def test_repair_payload_updates_both_specs_sections(self):
        payload = {
            'detailed_specs': {
                'general': {
                    'Dryer': 'yes',
                    'Drying capacity': '6 kg',
                }
            },
            'raw_specs': {
                'general': {
                    'Dryer': 'yes',
                    'Drying capacity': '6 kg',
                }
            },
        }

        fixed = repair_payload(payload, 'en')

        self.assertEqual(fixed['detailed_specs']['general']['Dryer'], 'no')
        self.assertEqual(fixed['raw_specs']['general']['Dryer'], 'no')
        self.assertNotIn('Drying capacity', fixed['detailed_specs']['general'])
        self.assertNotIn('Drying capacity', fixed['raw_specs']['general'])

    def test_extract_drying_flag_from_html_returns_false_for_cross_icon(self):
        html = """
        <tr valign='top'>
            <td width='49%' class='op1'><span class='gloss'><span class='nobr'>Сушка</span></span></td>
            <td width="51%" class="op3"><img class="prop-n" src="/img/table-none-1.gif" alt=""></td>
        </tr>
        """

        self.assertFalse(extract_drying_flag_from_html(html))

    def test_extract_drying_flag_from_html_returns_true_for_check_icon(self):
        html = """
        <tr valign='top'>
            <td width='49%' class='op1'><span class='gloss'><span class='nobr'>Сушка</span></span></td>
            <td width="51%" class="op3"><img class="prop-y" src="/img/icons/bul_141.gif" alt=""></td>
        </tr>
        """

        self.assertTrue(extract_drying_flag_from_html(html))

    def test_specs_need_page_check_detects_yes_without_capacity(self):
        specs = {
            'general': {
                'Сушилка': 'да',
                'Загрузка': '6 кг',
            }
        }

        self.assertTrue(specs_need_page_check(specs, 'ru'))


class BreakdownSlugTests(SimpleTestCase):
    def test_slug_ignores_device_model_codes_after_dash(self):
        breakdown = SimpleNamespace(
            id=1,
            title='Code E6 — battery overheating on Dreame H11, H11 Max wet dry vacuum',
            title_ua='',
            title_en='Code E6 — battery overheating on Dreame H11, H11 Max wet dry vacuum',
            description='',
            description_ua='',
            description_en='',
        )

        self.assertEqual(views._get_breakdown_slug(breakdown, 'en'), 'e6')

    def test_slug_uses_real_error_phrase_and_ignores_model_name(self):
        breakdown = SimpleNamespace(
            id=2,
            title='Сообщение Air Duct Blocked — засор воздушного тракта в вертикальном пылесосе Dreame R20',
            title_ua='',
            title_en='',
            description='',
            description_ua='',
            description_en='',
        )

        self.assertEqual(views._get_breakdown_slug(breakdown, 'ru'), 'air_duct_blocked')

    def test_slug_collects_mixed_digit_and_letter_codes(self):
        breakdown = SimpleNamespace(
            id=3,
            title='Коды E1, EE, EF — ошибка двигателя в моющем пылесосе Dreame H11, H11 Max, H12',
            title_ua='',
            title_en='',
            description='',
            description_ua='',
            description_en='',
        )

        self.assertEqual(views._get_breakdown_slug(breakdown, 'ru'), 'e1_ee_ef')


class ProductAdminFormTests(TestCase):
    def test_brand_queryset_is_limited_by_instance_category(self):
        cleaners, _ = Category.objects.get_or_create(
            id_name='cleaners',
            defaults={
                'name_ru': 'Пылесосы',
                'name_ua': 'Пилососи',
                'name_en': 'Vacuum Cleaners',
                'folder': 'last_cleaners',
            },
        )
        ovens = Category.objects.create(
            id_name='ovens',
            name_ru='Духовые шкафы',
            name_ua='Духові шафи',
            name_en='Ovens',
            folder='last_ovens',
        )
        vacuum_brand = VacuumBrand.objects.create(category=cleaners, name='TestBrand', slug='testbrand')
        oven_brand = VacuumBrand.objects.create(category=ovens, name='TestBrand', slug='testbrand')

        form = ProductAdminForm(initial={'category': cleaners.id})

        self.assertIn(vacuum_brand, form.fields['brand'].queryset)
        self.assertNotIn(oven_brand, form.fields['brand'].queryset)

    def test_breakdown_group_queryset_shows_all_groups_in_selected_category(self):
        cleaners = Category.objects.create(
            id_name='cleaners-product-admin',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_cleaners',
        )
        other_category = Category.objects.create(
            id_name='ovens-product-admin',
            name_ru='Духовые шкафы',
            name_ua='Духові шафи',
            name_en='Ovens',
            folder='last_ovens',
        )
        samsung = VacuumBrand.objects.create(category=cleaners, name='Samsung', slug='samsung-cleaners')
        lg = VacuumBrand.objects.create(category=cleaners, name='LG', slug='lg-cleaners')
        other_brand = VacuumBrand.objects.create(category=other_category, name='Samsung', slug='samsung-ovens')
        common_group = BreakdownGroup.objects.create(category=cleaners, brand=None, name='Общие')
        samsung_group = BreakdownGroup.objects.create(category=cleaners, brand=samsung, name='Пылесосы Samsung')
        BreakdownGroup.objects.create(category=cleaners, brand=lg, name='Пылесосы LG')
        BreakdownGroup.objects.create(category=other_category, brand=other_brand, name='Духовые шкафы Samsung')

        form = ProductAdminForm(initial={'category': cleaners.id, 'brand': samsung.id})

        self.assertIn(common_group, form.fields['breakdown_group'].queryset)
        self.assertIn(samsung_group, form.fields['breakdown_group'].queryset)
        self.assertEqual(form.fields['breakdown_group'].queryset.count(), 3)
        self.assertIn(common_group, form.fields['breakdown_groups'].queryset)
        self.assertIn(samsung_group, form.fields['breakdown_groups'].queryset)
        self.assertEqual(form.fields['breakdown_groups'].queryset.count(), 3)

    def test_breakdown_group_queryset_without_brand_shows_all_category_groups(self):
        cleaners = Category.objects.create(
            id_name='cleaners-product-admin-no-brand',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_cleaners',
        )
        samsung = VacuumBrand.objects.create(category=cleaners, name='Samsung', slug='samsung-cleaners-no-brand')
        common_group = BreakdownGroup.objects.create(category=cleaners, brand=None, name='Общие')
        BreakdownGroup.objects.create(category=cleaners, brand=samsung, name='Пылесосы Samsung')

        form = ProductAdminForm(initial={'category': cleaners.id})

        self.assertIn(common_group, form.fields['breakdown_group'].queryset)
        self.assertEqual(form.fields['breakdown_group'].queryset.count(), 2)

    def test_product_form_removes_primary_group_from_additional_groups(self):
        cleaners = Category.objects.create(
            id_name='cleaners-product-admin-remove-duplicate',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_cleaners',
        )
        brand = VacuumBrand.objects.create(category=cleaners, name='Samsung', slug='samsung-cleaners-remove-duplicate')
        primary_group = BreakdownGroup.objects.create(category=cleaners, brand=None, name='Общие')
        extra_group = BreakdownGroup.objects.create(category=cleaners, brand=brand, name='Пылесосы Samsung')

        form = ProductAdminForm(
            data={
                'category': cleaners.id,
                'brand': brand.id,
                'breakdown_group': primary_group.id,
                'breakdown_groups': [primary_group.id, extra_group.id],
                'name_ru': 'Товар',
                'description_ru': '',
                'specs_ru': '{"Тип":"ручной"}',
                'name_ua': 'Товар',
                'description_ua': '',
                'specs_ua': '{"Тип":"ручний"}',
                'name_en': 'Product',
                'description_en': '',
                'specs_en': '{"Type":"manual"}',
                'images': '["https://example.com/image.jpg"]',
            }
        )

        self.assertTrue(form.is_valid())
        self.assertNotIn(primary_group, form.cleaned_data['breakdown_groups'])
        self.assertIn(extra_group, form.cleaned_data['breakdown_groups'])


class BreakdownGroupAdminFormTests(TestCase):
    def test_brand_queryset_is_limited_by_selected_category(self):
        fridges = Category.objects.create(
            id_name='fridges-admin',
            name_ru='Холодильники',
            name_ua='Холодильники',
            name_en='Refrigerators',
            folder='last_fridges',
        )
        microwaves = Category.objects.create(
            id_name='microwaves-admin',
            name_ru='Микроволновые печи',
            name_ua='Мікрохвильові печі',
            name_en='Microwaves',
            folder='last_microwaves',
        )
        fridge_brand = VacuumBrand.objects.create(category=fridges, name='Fridge Brand', slug='fridge-brand')
        microwave_brand = VacuumBrand.objects.create(category=microwaves, name='Microwave Brand', slug='microwave-brand')

        form = BreakdownGroupAdminForm(initial={'category': fridges.id})

        self.assertIn(fridge_brand, form.fields['brand'].queryset)
        self.assertNotIn(microwave_brand, form.fields['brand'].queryset)

    def test_breakdown_group_string_representation_uses_group_name(self):
        category = Category.objects.create(
            id_name='washers-admin',
            name_ru='Стиральные машины',
            name_ua='Пральні машини',
            name_en='Washing Machines',
            folder='last_washers',
        )
        brand = VacuumBrand.objects.create(category=category, name='Laundry Brand', slug='laundry-brand')
        breakdown_group = BreakdownGroup.objects.create(
            category=category,
            brand=brand,
            name='Стиральные машины Laundry Brand',
        )
        breakdown = Breakdown.objects.create(
            breakdown_group=breakdown_group,
            title='Не включается',
            possible_causes='Нет питания',
            what_to_check='Проверить розетку',
            how_to_fix='Заменить кабель',
        )

        self.assertEqual(str(breakdown_group), 'Стиральные машины Laundry Brand')
        self.assertEqual(str(breakdown), 'Не включается — Стиральные машины Laundry Brand')

    def test_brand_is_required_for_breakdown_group(self):
        category = Category.objects.create(
            id_name='vacuums-admin-no-brand',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_vacuums',
        )

        form = BreakdownGroupAdminForm(
            data={
                'category': category.id,
                'brand': '',
                'name': 'Общие поломки',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('brand', form.errors)

    def test_breakdown_group_name_is_generated_from_category_and_brand(self):
        category = Category.objects.create(
            id_name='vacuums-admin-name',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_vacuums_name',
        )
        brand = VacuumBrand.objects.create(category=category, name='Samsung', slug='samsung-vacuums-name')

        form = BreakdownGroupAdminForm(
            data={
                'category': category.id,
                'brand': brand.id,
                'name': '',
            }
        )

        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.name, 'Пылесосы Samsung')

    def test_breakdown_group_custom_name_is_preserved(self):
        category = Category.objects.create(
            id_name='vacuums-admin-custom-name',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_vacuums_custom_name',
        )
        brand = VacuumBrand.objects.create(category=category, name='Samsung', slug='samsung-vacuums-custom-name')

        form = BreakdownGroupAdminForm(
            data={
                'category': category.id,
                'brand': brand.id,
                'name': 'Пылесосы Samsung — Дополнительная группа',
            }
        )

        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.name, 'Пылесосы Samsung — Дополнительная группа')

    def test_breakdown_fields_are_optional(self):
        category = Category.objects.create(
            id_name='vacuums-admin-optional-breakdown',
            name_ru='Пылесосы',
            name_ua='Пилососи',
            name_en='Vacuum Cleaners',
            folder='last_vacuums_optional',
        )
        brand = VacuumBrand.objects.create(category=category, name='Optional Brand', slug='optional-brand')
        breakdown_group = BreakdownGroup.objects.create(category=category, brand=brand, name='')
        breakdown = Breakdown(
            breakdown_group=breakdown_group,
            title='',
            possible_causes='',
            what_to_check='',
            how_to_fix='',
            title_ua='',
            possible_causes_ua='',
            what_to_check_ua='',
            how_to_fix_ua='',
            title_en='',
            possible_causes_en='',
            what_to_check_en='',
            how_to_fix_en='',
        )

        breakdown.full_clean()


class SectionViewFiltersTests(TestCase):
    def setUp(self):
        self.cleaners, _ = Category.objects.get_or_create(
            id_name='cleaners',
            defaults={
                'name_ru': 'Пылесосы',
                'name_ua': 'Пилососи',
                'name_en': 'Vacuum Cleaners',
                'folder': 'last_cleaners',
            },
        )
        self.other_section, _ = Category.objects.get_or_create(
            id_name='other-section',
            defaults={
                'name_ru': 'Прочая техника',
                'name_ua': 'Інша техніка',
                'name_en': 'Other Appliances',
                'folder': 'other_section',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.other_section, name='Brand A', slug='brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.other_section, name='Brand B', slug='brand-b')

        self.section_product_a = Product.objects.create(
            category=self.other_section,
            brand=self.brand_a,
            name_ru='Товар A',
            description_ru='Описание A',
            specs_ru={'general': {'Тип': 'электрическая'}},
        )
        self.section_product_b = Product.objects.create(
            category=self.other_section,
            brand=self.brand_b,
            name_ru='Товар B',
            description_ru='Описание B',
            specs_ru={'general': {'Тип': 'газовая'}},
        )
        Product.objects.create(
            category=self.cleaners,
            name_ru='Пылесос',
            description_ru='Описание пылесоса',
            specs_ru={'general': {'Тип': 'обычный'}},
            product_folder='test_cleaner',
        )

    def test_non_vacuum_section_shows_only_brand_filter(self):
        response = self.client.get(reverse('product_section', args=['ru', self.other_section.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['vacuum_filter_groups'], [])
        self.assertEqual(len(response.context['brands']), 2)

    def test_non_vacuum_section_ignores_spec_filters_but_keeps_brand_filter(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.other_section.id_name]),
            {'brand': ['brand-a'], 'sf_tip': ['газовая']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['vacuum_filter_groups'], [])
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.section_product_a.id],
        )


class CoffeeMachineFiltersTests(TestCase):
    def setUp(self):
        self.coffeemachines, _ = Category.objects.get_or_create(
            id_name='coffeemachines',
            defaults={
                'name_ru': 'Кофемашины',
                'name_ua': 'Кавомашини',
                'name_en': 'Coffee Machines',
                'folder': 'last_CoffeeMachines',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.coffeemachines, name='Coffee Brand A', slug='coffee-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.coffeemachines, name='Coffee Brand B', slug='coffee-brand-b')

        self.automatic_machine = Product.objects.create(
            category=self.coffeemachines,
            brand=self.brand_a,
            name_ru='Автоматическая кофемашина',
            description_ru='Автоматическая кофемашина',
            specs_ru={
                'general': {
                    'Тип': 'эспрессо (автоматическая)',
                    'Используемый кофе': 'в зернах молотый',
                    'Режимы': 'капучино горячая вода',
                    'Приготовление молочных напитков': 'автоматическое',
                    'Регулировки': 'крепость напитка объем напитка',
                    'Встроенная кофемолка': 'керамические жернова',
                    'Функции и возможности': 'самоочистка фильтр для воды сенсорный дисплей',
                    'Давление': '15 бар',
                    'Потребляемая мощность': '1500 Вт',
                    'Резервуар для воды': '1.8 л',
                    'Емкость кофемолки': '275 г',
                },
            },
        )
        self.capsule_machine = Product.objects.create(
            category=self.coffeemachines,
            brand=self.brand_b,
            name_ru='Капсульная кофемашина',
            description_ru='Капсульная кофемашина',
            specs_ru={
                'general': {
                    'Тип': 'капсульная',
                    'Используемый кофе': 'в капсулах',
                    'Совместимые капсулы': 'Nespresso Original',
                    'Приготовление молочных напитков': 'отсутствует',
                    'Давление': '19 бар',
                    'Потребляемая мощность': '1400 Вт',
                    'Резервуар для воды': '700 мл',
                },
            },
        )

    def test_coffee_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.coffeemachines.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'coffee_type')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'cf_coffee_type')

    def test_coffee_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.coffeemachines.id_name]),
            {'cf_coffee_type': ['2'], 'brand': ['coffee-brand-a']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.automatic_machine.id],
        )
        self.assertNotIn(self.capsule_machine.id, [product.id for product in response.context['products'].object_list])


class CookersFiltersTests(TestCase):
    def setUp(self):
        self.cookers, _ = Category.objects.get_or_create(
            id_name='cookers',
            defaults={
                'name_ru': 'Плиты',
                'name_ua': 'Плити',
                'name_en': 'Cookers',
                'folder': 'last_cookers',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.cookers, name='Cooker Brand A', slug='cooker-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.cookers, name='Cooker Brand B', slug='cooker-brand-b')

        self.gas_cooker = Product.objects.create(
            category=self.cookers,
            brand=self.brand_a,
            name_ru='Газовая плита',
            description_ru='Газовая плита',
            specs_ru={
                'general': {
                    'Тип варочной поверхности': 'газовая',
                    'Управление конфорками': 'поворотные переключатели',
                    'Рабочая поверхность': 'эмалированная',
                    'Тип духовки': 'газовая',
                    'Объем духовки': '59 л',
                    'Мощность подключения': '1.7 кВт',
                    'Функции': 'таймер\nгриль',
                    'Кол-во газовых конфорок': '4 шт',
                    'Решетки конфорок': 'чугунные',
                    'Крышка': 'стеклянная',
                    'Страна производства': 'Румыния',
                    'Класс энергопотребления': 'A',
                    'Кол-во стекол дверцы': '3',
                    'Автоподжиг': 'варочной поверхности / духовки',
                    'Газ-контроль': 'варочной поверхности / духовки',
                    'Тип очистки внутренней поверхности': 'традиционный',
                    'Габариты (ВхШхГ)': '85.5x50x60 см',
                },
            },
        )
        self.tabletop_induction = Product.objects.create(
            category=self.cookers,
            brand=self.brand_b,
            name_ru='Настольная индукционная плита',
            description_ru='Настольная индукционная плита',
            specs_ru={
                'general': {
                    'Тип варочной поверхности': 'электрическая',
                    'Управление конфорками': 'сенсорное',
                    'Рабочая поверхность': 'стеклокерамика',
                    'Мощность подключения': '2 кВт',
                    'Автоматическое отключение': 'варочной поверхности',
                    'Защита от детей': 'да',
                    'Кол-во индукционных конфорок': '1 шт',
                    'Габариты (ВхШхГ)': '4.5x29x36.5 см',
                },
            },
        )

    def test_cookers_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.cookers.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'cooker_type')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'kf_cooker_type')

    def test_cookers_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.cookers.id_name]),
            {'kf_cooker_type': ['0'], 'kf_burner_type': ['2'], 'brand': ['cooker-brand-b']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.tabletop_induction.id],
        )
        self.assertNotIn(self.gas_cooker.id, [product.id for product in response.context['products'].object_list])


class DishwashersFiltersTests(TestCase):
    def setUp(self):
        self.dishwashers, _ = Category.objects.get_or_create(
            id_name='dishwashers',
            defaults={
                'name_ru': 'Посудомоечные машины',
                'name_ua': 'Посудомийні машини',
                'name_en': 'Dishwashers',
                'folder': 'last_Dishwashers',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.dishwashers, name='Dishwasher Brand A', slug='dishwasher-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.dishwashers, name='Dishwasher Brand B', slug='dishwasher-brand-b')

        self.compact_dishwasher = Product.objects.create(
            category=self.dishwashers,
            brand=self.brand_a,
            name_ru='Компактная посудомоечная машина',
            description_ru='Компактная посудомоечная машина',
            specs_ru={
                'general': {
                    'Кол-во комплектов посуды': '6',
                    'Расход воды за цикл': '7 л',
                    'Сушка': 'конденсационная',
                    'Ключевые программы': 'быстрая мойка\nэкономная',
                    'Не требуется водопровод': 'да',
                    'Управление': 'кнопочные переключатели',
                    'Дисплей': 'LED',
                    'Класс энергопотребления': 'A++',
                    'Уровень шума': '49 дБ',
                    'Габариты (ВхШхГ)': '43.8x55x50 см',
                    'Страна производства': 'Китай',
                },
            },
        )
        self.floorstanding_dishwasher = Product.objects.create(
            category=self.dishwashers,
            brand=self.brand_b,
            name_ru='Напольная посудомоечная машина',
            description_ru='Напольная посудомоечная машина',
            specs_ru={
                'general': {
                    'Кол-во комплектов посуды': '10',
                    'Расход воды за цикл': '9 л',
                    'Сушка': 'обдув',
                    'Ключевые программы': 'половинная загрузка\nавтоматическая\nгигиеническая',
                    'Дополнительные форсунки': 'да',
                    'Регулировка верхней корзины': 'да',
                    'Таймер отсрочки запуска': 'да',
                    'Управление': 'сенсорное',
                    'Защита от детей': 'да',
                    'Класс энергопотребления (new)': 'D',
                    'Уровень шума': '44 дБ',
                    'Габариты (ВхШхГ)': '84.5x45x60 см',
                    'Страна производства': 'Польша',
                },
            },
        )

    def test_dishwashers_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.dishwashers.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'dishwasher_format')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'df_dishwasher_format')

    def test_dishwashers_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.dishwashers.id_name]),
            {'df_dishwasher_format': ['1'], 'df_dishwasher_controls': ['1'], 'df_dishwasher_energy_class': ['2'], 'brand': ['dishwasher-brand-b']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.floorstanding_dishwasher.id],
        )
        self.assertNotIn(self.compact_dishwasher.id, [product.id for product in response.context['products'].object_list])


class FridgesFiltersTests(TestCase):
    def setUp(self):
        self.fridges, _ = Category.objects.get_or_create(
            id_name='fridges',
            defaults={
                'name_ru': 'Холодильники',
                'name_ua': 'Холодильники',
                'name_en': 'Refrigerators',
                'folder': 'last_fridges',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.fridges, name='Fridge Brand A', slug='fridge-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.fridges, name='Fridge Brand B', slug='fridge-brand-b')

        self.classic_fridge = Product.objects.create(
            category=self.fridges,
            brand=self.brand_a,
            name_ru='Классический холодильник',
            description_ru='Классический холодильник',
            specs_ru={
                'general': {
                    'Тип': 'классический',
                    'Количество камер': '2',
                    'Морозильная камера': 'сверху',
                    'Функции': 'перевешивание дверей\nLED освещение',
                    'Дополнительно': 'скрытые дверные ручки',
                    'Объем холодильной камеры': '126 л',
                    'Полок': '3 шт',
                    'Объем морозильной камеры': '41 л',
                    'Отделений морозильной камеры': '2 шт',
                    'Время сохранения холода': '12 ч',
                    'Управление': 'поворотные переключатели',
                    'Класс энергопотребления (new)': 'E',
                    'Климатический класс': 'ST (+18...+38 °С)',
                    'Уровень шума': '40 дБ',
                    'Габариты (ВхШхГ)': '122x54x57 см',
                    'Страна производства': 'Китай',
                    'Дата добавления на E-Katalog': 'апрель 2024',
                },
            },
        )
        self.french_door_fridge = Product.objects.create(
            category=self.fridges,
            brand=self.brand_b,
            name_ru='French-door холодильник',
            description_ru='French-door холодильник',
            specs_ru={
                'general': {
                    'Тип': 'French-door (распашной)',
                    'Количество камер': '3',
                    'No Frost': 'морозильная / холодильная камеры',
                    'Функции': 'режим отпуска\nзащита от детей\nLED дисплей\nиндикатор закрытия дверцы\nуправление со смартфона (Wi-Fi)',
                    'Дополнительно': 'скрытые дверные ручки',
                    'Объем холодильной камеры': '388 л',
                    'Полок': '3 шт',
                    'Быстрое охлаждение': 'да',
                    'Динамическое охлаждение': 'да',
                    'Морозильная камера': 'снизу (выдвижная)',
                    'Объем морозильной камеры': '206 л',
                    'Отделений морозильной камеры': '6 шт / 4 ящика, 2 полки /',
                    'Мощность замораживания': '12 кг/сутки',
                    'Управление': 'сенсорное внешнее',
                    'Класс энергопотребления (new)': 'E',
                    'Климатический класс': 'SN, N, ST, T (+10...+43 °С)',
                    'Уровень шума': '37 дБ',
                    'Габариты (ВхШхГ)': '187.4x90.9x69.8 см',
                    'Страна производства': 'Польша',
                    'Дата добавления на E-Katalog': 'май 2025',
                },
            },
        )

    def test_fridges_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.fridges.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'fridge_type')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'rf_fridge_type')

    def test_fridges_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.fridges.id_name]),
            {'rf_fridge_type': ['2'], 'rf_fridge_controls': ['3'], 'rf_fridge_energy_class': ['4'], 'brand': ['fridge-brand-b']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.french_door_fridge.id],
        )
        self.assertNotIn(self.classic_fridge.id, [product.id for product in response.context['products'].object_list])


class HobsFiltersTests(TestCase):
    def setUp(self):
        self.hobs, _ = Category.objects.get_or_create(
            id_name='hobs',
            defaults={
                'name_ru': 'Варочные поверхности',
                'name_ua': 'Варильні поверхні',
                'name_en': 'Hobs',
                'folder': 'last_Hobs',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.hobs, name='Hob Brand A', slug='hob-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.hobs, name='Hob Brand B', slug='hob-brand-b')

        self.gas_hob = Product.objects.create(
            category=self.hobs,
            brand=self.brand_a,
            name_ru='Газовая варочная поверхность',
            description_ru='Газовая варочная поверхность',
            specs_ru={
                'general': {
                    'Устройство': 'варочная поверхность',
                    'Тип поверхности': 'газовая',
                    'Кол-во газовых конфорок': '4',
                    'Рабочая поверхность': 'закаленное стекло',
                    'Управление': 'поворотные переключатели спереди',
                    'Газ-контроль': 'да',
                    'Автоподжиг': 'да',
                    'Мощность конфорок': '1 / 1.75 / 1.75 / 2.8 кВт',
                    'Мощность подключения': '7.3 кВт',
                    'Габариты (ШхГ)': '60x51 см',
                    'Размеры для встраивания (ШхГ)': '560x490 мм',
                    'Рамка': 'с рамкой',
                    'Решетки конфорок': 'чугунные',
                    'Страна производства': 'Турция',
                    'Дата добавления на E-Katalog': 'март 2024',
                },
            },
        )
        self.induction_hob = Product.objects.create(
            category=self.hobs,
            brand=self.brand_b,
            name_ru='Индукционная варочная поверхность домино',
            description_ru='Индукционная варочная поверхность домино',
            specs_ru={
                'general': {
                    'Устройство': 'варочная поверхность',
                    'Тип поверхности': 'индукционная',
                    'Кол-во индукционных конфорок': '2',
                    'Рабочая поверхность': 'стеклокерамика',
                    'Управление': 'сенсорный слайдер',
                    'Адаптивная зона (FlexZone)': 'да',
                    'Режим «мост» (Bridge)': 'да',
                    'Уровней мощности конфорок': '14',
                    'Дисплей': 'цифровой',
                    'Защита от детей': 'да',
                    'Мощность конфорок': '1.4 / 2.1 кВт',
                    'Мощность подключения': '3.5 кВт',
                    'Габариты (ШхГ)': '28.8x52 см',
                    'Размеры для встраивания (ШхГ)': '268x500 мм',
                    'Рамка': 'отсутствует',
                    'Страна производства': 'Германия',
                    'Дата добавления на E-Katalog': 'июнь 2025',
                },
            },
        )

    def test_hobs_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.hobs.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'hob_device')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'hf_hob_device')

    def test_hobs_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.hobs.id_name]),
            {'hf_hob_burner_type': ['2'], 'hf_hob_controls': ['4'], 'hf_hob_design': ['1'], 'brand': ['hob-brand-b']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.induction_hob.id],
        )
        self.assertNotIn(self.gas_hob.id, [product.id for product in response.context['products'].object_list])


class OvensFiltersTests(TestCase):
    def setUp(self):
        self.ovens, _ = Category.objects.get_or_create(
            id_name='ovens',
            defaults={
                'name_ru': 'Духовые шкафы',
                'name_ua': 'Духові шафи',
                'name_en': 'Ovens',
                'folder': 'last_ovens',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.ovens, name='Oven Brand A', slug='oven-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.ovens, name='Oven Brand B', slug='oven-brand-b')

        self.smart_oven = Product.objects.create(
            category=self.ovens,
            brand=self.brand_a,
            name_ru='Умный электрический духовой шкаф',
            description_ru='Духовой шкаф с TFT дисплеем и мобильным приложением',
            specs_ru={
                'general': {
                    'Тип': 'электрический духовой шкаф',
                    'Органы управления': 'сенсоры',
                    'Объем': '71 л',
                    'Температура готовки': '30 – 300 °C',
                    'Режимы готовки': 'гриль\nконвекция\nсвоя программа\nразморозка',
                    'Кол-во режимов': '12 шт',
                    'Автоматических программ': '20 шт',
                    'Функции': 'таймер\nавтоматическое отключение\nмобильное приложение\nTFT дисплей\nзащита от детей',
                    'Кол-во стекол дверцы': '4',
                    'Направляющие противней': 'телескопические на одном уровне',
                    'Очистка внутренних стенок': 'пиролитическая',
                    'Класс энергопотребления': 'A++',
                    'Мощность подключения': '3.5 кВт',
                    'Габариты (ВхШхГ)': '59.4x59.5x56.7 см',
                    'Размеры для встраивания (ВхШхГ)': '590x560x550 мм',
                    'Страна производства': 'Германия',
                    'Дата добавления на E-Katalog': 'март 2025',
                },
            },
        )
        self.gas_oven = Product.objects.create(
            category=self.ovens,
            brand=self.brand_b,
            name_ru='Газовый духовой шкаф',
            description_ru='Газовый духовой шкаф с поворотными переключателями',
            specs_ru={
                'general': {
                    'Тип': 'газовый духовой шкаф',
                    'Органы управления': 'поворотные переключатели',
                    'Объем': '58 л',
                    'Температура готовки': '50 – 250 °C',
                    'Режимы готовки': 'гриль',
                    'Кол-во режимов': '4 шт',
                    'Функции': 'таймер',
                    'Кол-во стекол дверцы': '2',
                    'Направляющие противней': 'решетчатые',
                    'Очистка внутренних стенок': 'каталитическая',
                    'Класс энергопотребления': 'A',
                    'Мощность подключения': '2.2 кВт',
                    'Габариты (ВхШхГ)': '59.5x59.5x55 см',
                    'Размеры для встраивания (ВхШхГ)': '600x560x560 мм',
                    'Страна производства': 'Турция',
                    'Дата добавления на E-Katalog': 'апрель 2024',
                },
            },
        )

    def test_ovens_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.ovens.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'oven_device_type')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'of_oven_device_type')

    def test_ovens_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.ovens.id_name]),
            {'of_oven_device_type': ['0'], 'of_oven_features_list': ['4'], 'of_oven_width_filter': ['1'], 'brand': ['oven-brand-a']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.smart_oven.id],
        )
        self.assertNotIn(self.gas_oven.id, [product.id for product in response.context['products'].object_list])


class WashingMachinesFiltersTests(TestCase):
    def setUp(self):
        self.wash, _ = Category.objects.get_or_create(
            id_name='wash',
            defaults={
                'name_ru': 'Стиральные машины',
                'name_ua': 'Пральні машини',
                'name_en': 'Washing Machines',
                'folder': 'last_wash',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.wash, name='Wash Brand A', slug='wash-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.wash, name='Wash Brand B', slug='wash-brand-b')

        self.smart_washer = Product.objects.create(
            category=self.wash,
            brand=self.brand_a,
            name_ru='Узкая стирально-сушильная машина',
            description_ru='Узкая фронтальная стиральная машина с Wi-Fi',
            specs_ru={
                'general': {
                    'Тип загрузки': 'фронтальная загрузка',
                    'Загрузка': '7 кг',
                    'Загрузка для сушки': '5 кг',
                    'Макс. скорость отжима': '1400 об/мин',
                    'Стирка паром': 'да',
                    'Автоматическое дозирование': 'да',
                    'Количество программ': '12 шт',
                    'Дополнительные программы': 'быстрая стирка\nсвоя программа\nсамоочистка',
                    'Управление': 'поворотная ручка + сенсоры',
                    'Управление со смартфона': 'Wi-Fi',
                    'Защита от протечек': 'да',
                    'Контроль дисбаланса': 'да',
                    'Контроль пенообразования': 'да',
                    'Защита от детей': 'да',
                    'Материал ТЭНа': 'никелированный ТЭН',
                    'Инверторный двигатель': 'да',
                    'Дисплей': 'TFT',
                    'Материал бака': 'нержавеющая сталь',
                    'Габариты (ВхШхГ)': '84.5x60x44 см',
                    'Класс энергопотребления (new)': 'A',
                    'Класс отжима': 'A',
                    'Уровень шума (отжим)': '72 дБ',
                    'Расход воды за цикл': '45 л',
                    'Открытие дверцы': 'влево',
                    'Угол открытия': '180°',
                    'Страна производства': 'Польша',
                    'Дата добавления на E-Katalog': 'январь 2026',
                },
            },
        )
        self.top_loader = Product.objects.create(
            category=self.wash,
            brand=self.brand_b,
            name_ru='Вертикальная стиральная машина',
            description_ru='Компактная вертикальная стиральная машина',
            specs_ru={
                'general': {
                    'Тип загрузки': 'вертикальная загрузка',
                    'Загрузка': '5 кг',
                    'Макс. скорость отжима': '1000 об/мин',
                    'Количество программ': '6 шт',
                    'Дополнительные программы': 'деликатная стирка',
                    'Управление': 'поворотная ручка + кнопки',
                    'Контроль дисбаланса': 'да',
                    'Материал ТЭНа': 'нержавеющая сталь',
                    'Дисплей': 'LED',
                    'Материал бака': 'пластик',
                    'Габариты (ВхШхГ)': '79x40x60 см',
                    'Класс энергопотребления': 'A+',
                    'Класс отжима': 'C',
                    'Уровень шума (отжим)': '79 дБ',
                    'Расход воды за цикл': '65 л',
                    'Открытие дверцы': 'вправо',
                    'Страна производства': 'Турция',
                    'Дата добавления на E-Katalog': 'май 2024',
                },
            },
        )
        self.no_dry_washer = Product.objects.create(
            category=self.wash,
            brand=self.brand_b,
            name_ru='Стиральная машина без сушки',
            description_ru='Фронтальная стиральная машина без функции сушки',
            specs_ru={
                'general': {
                    'Тип загрузки': 'фронтальная загрузка',
                    'Загрузка': '8 кг',
                    'Макс. скорость отжима': '1200 об/мин',
                    'Сушилка': 'нет',
                    'Функции и возможности': 'без сушилки\nтаймер окончания стирки',
                    'Управление': 'сенсорное',
                    'Дисплей': 'LED',
                    'Габариты (ВхШхГ)': '84.5x60x50 см',
                    'Класс энергопотребления': 'A++',
                    'Страна производства': 'Турция',
                    'Дата добавления на E-Katalog': 'февраль 2025',
                },
            },
        )

    def test_washing_machines_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.wash.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'wash_type')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'wf_wash_type')

    def test_washing_machines_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.wash.id_name]),
            {'wf_wash_type': ['0'], 'wf_wash_features': ['10'], 'wf_wash_controls': ['4'], 'brand': ['wash-brand-a']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.smart_washer.id],
        )
        self.assertNotIn(self.top_loader.id, [product.id for product in response.context['products'].object_list])

    def test_washing_machines_drying_filter_distinguishes_without_dryer(self):
        with_dryer_response = self.client.get(
            reverse('product_section', args=['ru', self.wash.id_name]),
            {'wf_wash_features': ['0']},
        )
        without_dryer_response = self.client.get(
            reverse('product_section', args=['ru', self.wash.id_name]),
            {'wf_wash_features': ['1']},
        )

        self.assertEqual(with_dryer_response.status_code, 200)
        self.assertEqual(without_dryer_response.status_code, 200)

        with_dryer_ids = [product.id for product in with_dryer_response.context['products'].object_list]
        without_dryer_ids = [product.id for product in without_dryer_response.context['products'].object_list]

        self.assertIn(self.smart_washer.id, with_dryer_ids)
        self.assertNotIn(self.no_dry_washer.id, with_dryer_ids)
        self.assertIn(self.no_dry_washer.id, without_dryer_ids)
        self.assertNotIn(self.smart_washer.id, without_dryer_ids)


class MicrowavesFiltersTests(TestCase):
    def setUp(self):
        self.microwaves, _ = Category.objects.get_or_create(
            id_name='microwaves',
            defaults={
                'name_ru': 'Микроволновые печи',
                'name_ua': 'Мікрохвильові печі',
                'name_en': 'Microwaves',
                'folder': 'last_Microwaves',
            },
        )
        self.brand_a = VacuumBrand.objects.create(category=self.microwaves, name='Microwave Brand A', slug='microwave-brand-a')
        self.brand_b = VacuumBrand.objects.create(category=self.microwaves, name='Microwave Brand B', slug='microwave-brand-b')

        self.grill_microwave = Product.objects.create(
            category=self.microwaves,
            brand=self.brand_a,
            name_ru='Микроволновка с грилем',
            description_ru='Микроволновка с грилем и сенсорным управлением',
            specs_ru={
                'general': {
                    'Объем': '23 л',
                    'Мощность микроволн': '900 Вт',
                    'Функции и возможности': 'гриль\nавторазмораживание\nавтоприготовление',
                    'Дополнительно': 'инвертор\nочистка паром',
                    'Органы управления': 'сенсорные',
                    'Внутреннее покрытие': 'керамика',
                    'Дверца': 'боковая',
                    'Открытие дверцы': 'кнопка',
                    'Диаметр столика': '270 мм',
                    'Дисплей': 'да',
                    'Защита от детей': 'да',
                    'Габариты (ВхШхГ)': '29x48x36 см',
                    'Дата добавления на E-Katalog': 'май 2025',
                },
            },
        )
        self.compact_microwave = Product.objects.create(
            category=self.microwaves,
            brand=self.brand_b,
            name_ru='Компактная микроволновка',
            description_ru='Компактная микроволновка без гриля и без поворотного столика',
            specs_ru={
                'general': {
                    'Объем': '17 л',
                    'Мощность микроволн': '700 Вт',
                    'Функции и возможности': 'авторазмораживание',
                    'Дополнительно': 'ретро дизайн\nбез поворотного столика',
                    'Органы управления': 'поворотные',
                    'Внутреннее покрытие': 'эмаль',
                    'Дверца': 'откидная',
                    'Открытие дверцы': 'ручка',
                    'Габариты (ВхШхГ)': '24x43x31 см',
                    'Дата добавления на E-Katalog': 'декабрь 2024',
                },
            },
        )

    def test_microwaves_section_shows_configured_filters(self):
        response = self.client.get(reverse('product_section', args=['ru', self.microwaves.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['vacuum_filter_groups'])
        self.assertEqual(response.context['vacuum_filter_groups'][0]['key'], 'microwave_capacity')
        self.assertEqual(response.context['vacuum_filter_groups'][0]['param'], 'mf_microwave_capacity')

    def test_microwaves_section_applies_configured_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.microwaves.id_name]),
            {'mf_microwave_power': ['2'], 'mf_microwave_features': ['0'], 'mf_microwave_extra': ['8'], 'brand': ['microwave-brand-a']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.id for product in response.context['products'].object_list],
            [self.grill_microwave.id],
        )
        self.assertNotIn(self.compact_microwave.id, [product.id for product in response.context['products'].object_list])


class ProductDuplicateChecksTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            id_name='duplicate-check',
            name_ru='Проверка дублей',
            name_ua='Перевірка дублів',
            name_en='Duplicate Check',
            folder='duplicate_check',
        )
        self.brand = VacuumBrand.objects.create(
            category=self.category,
            name='DuplicateBrand',
            slug='duplicate-brand',
        )

    def test_collect_product_duplicates_finds_exact_name_matches(self):
        first = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='Одинаковое название',
            name_ua='Однакова назва',
            name_en='Same name',
        )
        second = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='  Одинаковое название  ',
            name_ua='Однакова назва',
            name_en='Same name',
        )
        Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='Другое название',
            name_ua='Інша назва',
            name_en='Different name',
        )

        duplicates = collect_product_duplicates()

        self.assertEqual(len(duplicates['name_ru']), 1)
        self.assertEqual(duplicates['name_ru'][0]['value'], 'Одинаковое название')
        self.assertEqual(
            sorted([item['id'] for item in duplicates['name_ru'][0]['items']]),
            sorted([first.id, second.id]),
        )

    def test_check_product_duplicates_command_fails_when_duplicates_exist(self):
        Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='Дубликат',
            name_ua='Дублікат',
            name_en='Duplicate',
        )
        Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='Дубликат',
            name_ua='Дублікат',
            name_en='Duplicate',
        )

        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command('check_product_duplicates', stdout=stdout)

        self.assertIn('Найдено групп дублей', stdout.getvalue())

    def test_check_product_duplicates_command_passes_when_no_duplicates_exist(self):
        Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='Уникальный товар',
            name_ua='Унікальний товар',
            name_en='Unique product',
        )

        stdout = StringIO()
        call_command('check_product_duplicates', stdout=stdout)

        self.assertIn('Дублей товаров не найдено.', stdout.getvalue())


class ProductDetailViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            id_name='fridges',
            name_ru='Холодильники',
            name_ua='Холодильники',
            name_en='Refrigerators',
            folder='last_fridges',
        )
        self.brand = VacuumBrand.objects.create(
            category=self.category,
            name='TestBrand',
            slug='testbrand',
        )
        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name_ru='Холодильник Тест',
            description_ru='Подробное описание холодильника',
            specs_ru={'general': {'Тип': 'двухкамерный', 'Высота': '185 см'}},
            name_ua='Холодильник Тест',
            description_ua='Детальний опис холодильника',
            specs_ua={'general': {'Тип': 'двокамерний', 'Висота': '185 см'}},
            name_en='Test Fridge',
            description_en='Detailed fridge description',
            specs_en={'general': {'Type': 'double-door', 'Height': '185 cm'}},
        )
        self.breakdown_group = BreakdownGroup.objects.create(
            category=self.category,
            brand=self.brand,
            name='Холодильники TestBrand',
        )
        self.breakdown = Breakdown.objects.create(
            breakdown_group=self.breakdown_group,
            title='Не включается',
            possible_causes='Нет питания',
            what_to_check='Проверить розетку',
            how_to_fix='Заменить кабель',
            title_ua='Не вмикається',
            possible_causes_ua='Немає живлення',
            what_to_check_ua='Перевірити розетку',
            how_to_fix_ua='Замінити кабель',
            title_en='Does not turn on',
            possible_causes_en='No power',
            what_to_check_en='Check the power outlet',
            how_to_fix_en='Replace the cable',
        )
        self.product.breakdown_group = self.breakdown_group
        self.product.save(update_fields=['breakdown_group'])

    def test_product_detail_route_supports_unicode_slug(self):
        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product'].id, self.product.id)
        self.assertContains(response, 'Подробное описание холодильника')

    def test_section_cards_include_product_detail_links(self):
        response = self.client.get(reverse('product_section', args=['ru', self.category.id_name]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            ),
        )

    def test_section_language_switcher_keeps_current_filters(self):
        response = self.client.get(
            reverse('product_section', args=['ru', self.category.id_name]),
            {'brand': ['testbrand'], 'page': 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['language_urls']['ua'],
            '/ua/products/fridges/?brand=testbrand&page=2',
        )
        self.assertContains(response, '/ua/products/fridges/?brand=testbrand&amp;page=2')

    def test_search_language_switcher_keeps_query_string(self):
        response = self.client.get(
            reverse('search', args=['ru']),
            {'q': 'Холодильник', 'page': 3},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['language_urls']['en'],
            '/en/search/?q=%D0%A5%D0%BE%D0%BB%D0%BE%D0%B4%D0%B8%D0%BB%D1%8C%D0%BD%D0%B8%D0%BA&page=3',
        )
        self.assertContains(
            response,
            '/en/search/?q=%D0%A5%D0%BE%D0%BB%D0%BE%D0%B4%D0%B8%D0%BB%D1%8C%D0%BD%D0%B8%D0%BA&amp;page=3',
        )

    def test_product_detail_language_switcher_keeps_current_product(self):
        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['language_urls']['en'],
            '/en/products/fridges/test_fridge/',
        )
        self.assertContains(response, '/en/products/fridges/test_fridge/')

    def test_product_detail_shows_breakdowns_block(self):
        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Поломки')
        self.assertContains(response, self.breakdown.title)
        self.assertContains(response, self.breakdown.possible_causes)
        self.assertContains(response, self.breakdown.what_to_check)
        self.assertContains(response, self.breakdown.how_to_fix)

    def test_product_detail_builds_breakdown_link_with_all_error_codes(self):
        self.breakdown.title = 'Код E0 / E1 / E011 / E012 / E013 — сбой электроники панели или силовой платы'
        self.breakdown.save(update_fields=['title'])

        expected_breakdown_slug = 'e0_e1_e011_e012_e013'
        expected_breakdown_url = reverse(
            'breakdown_detail',
            args=[
                'ru',
                self.category.id_name,
                views._get_product_slug(self.product, 'ru'),
                expected_breakdown_slug,
            ],
        )

        product_detail_response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(product_detail_response.status_code, 200)
        self.assertContains(product_detail_response, expected_breakdown_url)

        breakdown_detail_response = self.client.get(expected_breakdown_url)
        self.assertEqual(breakdown_detail_response.status_code, 200)
        self.assertContains(breakdown_detail_response, self.breakdown.title)

    def test_product_detail_hides_empty_breakdown_fields(self):
        self.breakdown.what_to_check = ''
        self.breakdown.save(update_fields=['what_to_check'])

        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Возможные причины')
        self.assertContains(response, self.breakdown.possible_causes)
        self.assertNotContains(response, 'Что проверить')
        self.assertNotContains(response, 'Проверить розетку')
        self.assertContains(response, 'Как исправить')
        self.assertContains(response, self.breakdown.how_to_fix)

    def test_product_detail_hides_breakdown_without_any_sections(self):
        self.breakdown.possible_causes = ''
        self.breakdown.what_to_check = ''
        self.breakdown.how_to_fix = ''
        self.breakdown.save(update_fields=['possible_causes', 'what_to_check', 'how_to_fix'])

        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Поломки')
        self.assertNotContains(response, self.breakdown.title)

    def test_product_detail_uses_ukrainian_breakdowns_for_ua_language(self):
        response = self.client.get(
            reverse(
                'product_detail',
                args=['ua', self.category.id_name, views._get_product_slug(self.product, 'ua')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Поломки')
        self.assertContains(response, self.breakdown.title_ua)
        self.assertContains(response, self.breakdown.possible_causes_ua)
        self.assertContains(response, self.breakdown.what_to_check_ua)
        self.assertContains(response, self.breakdown.how_to_fix_ua)
        self.assertNotContains(response, self.breakdown.title_en)

    def test_product_detail_uses_english_breakdowns_for_en_language(self):
        response = self.client.get(
            reverse(
                'product_detail',
                args=['en', self.category.id_name, views._get_product_slug(self.product, 'en')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Breakdowns')
        self.assertContains(response, self.breakdown.title_en)
        self.assertContains(response, self.breakdown.possible_causes_en)
        self.assertContains(response, self.breakdown.what_to_check_en)
        self.assertContains(response, self.breakdown.how_to_fix_en)
        self.assertNotContains(response, self.breakdown.title_ua)

    def test_product_detail_shows_breakdowns_from_additional_groups(self):
        second_group = BreakdownGroup.objects.create(
            category=self.category,
            brand=self.brand,
            name='Холодильники TestBrand — Дополнительная',
        )
        second_breakdown = Breakdown.objects.create(
            breakdown_group=second_group,
            title='Шумит',
            possible_causes='Неправильная установка',
            what_to_check='Проверить уровень',
            how_to_fix='Отрегулировать ножки',
            title_ua='Гуде',
            possible_causes_ua='Неправильне встановлення',
            what_to_check_ua='Перевірити рівень',
            how_to_fix_ua='Відрегулювати ніжки',
            title_en='Makes noise',
            possible_causes_en='Improper installation',
            what_to_check_en='Check leveling',
            how_to_fix_en='Adjust the feet',
        )
        self.product.breakdown_groups.add(second_group)

        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.breakdown.title)
        self.assertContains(response, second_breakdown.title)

    def test_product_detail_shows_common_and_brand_groups_without_manual_link(self):
        common_group = BreakdownGroup.objects.create(
            category=self.category,
            brand=None,
            name='Холодильники Общие',
        )
        common_breakdown = Breakdown.objects.create(
            breakdown_group=common_group,
            title='Не морозит',
            possible_causes='Сбой термостата',
            what_to_check='Проверить режим',
            how_to_fix='Вызвать мастера',
            title_ua='Не морозить',
            possible_causes_ua='Збій термостата',
            what_to_check_ua='Перевірити режим',
            how_to_fix_ua='Викликати майстра',
            title_en='Not cooling',
            possible_causes_en='Thermostat issue',
            what_to_check_en='Check the mode',
            how_to_fix_en='Call service',
        )
        self.product.breakdown_group = common_group
        self.product.save(update_fields=['breakdown_group'])
        self.product.breakdown_groups.clear()

        response = self.client.get(
            reverse(
                'product_detail',
                args=['ru', self.category.id_name, views._get_product_slug(self.product, 'ru')],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, common_breakdown.title)
        self.assertContains(response, self.breakdown.title)
