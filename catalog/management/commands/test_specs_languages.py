import os
import re

from django.core.management.base import BaseCommand

from catalog.models import Product

CYR = re.compile(r"[А-Яа-яЁёІіЇїЄєҐґ]")
LAT = re.compile(r"[A-Za-z]")
UA_MARK = re.compile(r"[ІіЇїЄєҐґ]")
RU_MARK = re.compile(r"[ЫыЭэЁёЪъ]")


def flatten_text(value):
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(flatten_text(item))
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


def is_empty_specs(value):
    return value in (None, "", {}, [])


def detect_language_from_specs(value):
    text = flatten_text(value)
    cyr = len(CYR.findall(text))
    lat = len(LAT.findall(text))
    ua = len(UA_MARK.findall(text))
    ru = len(RU_MARK.findall(text))

    if not text.strip():
        return "unknown"

    if lat >= 8 and lat >= cyr * 1.3:
        return "en"

    if cyr >= 4:
        if ua > ru:
            return "ua"
        if ru > ua:
            return "ru"
        if lat > 0 and cyr > 0:
            return "mixed"
        return "unknown"

    if lat > 0:
        return "en"

    return "unknown"


def get_product_model(product):
    return (
        (product.name_ru or "").strip()
        or (product.name_ua or "").strip()
        or (product.name_en or "").strip()
        or ""
    )


def format_issue_line(item):
    return (
        f"{item['product_model']} | id={item['product_id']} | {item['field']} | "
        f"expected={item['expected_language']} | detected={item['detected_language']}"
    )


def build_report():
    products = Product.objects.all().only("id", "product_folder", "name_ru", "name_ua", "name_en", "specs_ru", "specs_ua", "specs_en")
    issues = []
    checked = 0

    for product in products.iterator():
        for lang in ("ru", "ua", "en"):
            field = f"specs_{lang}"
            specs_value = getattr(product, field)
            checked += 1

            if is_empty_specs(specs_value):
                issues.append(
                    {
                        "product_id": product.id,
                        "product_model": get_product_model(product),
                        "product_folder": product.product_folder,
                        "field": field,
                        "issue_type": "empty_specs",
                        "expected_language": lang,
                        "detected_language": "empty",
                    }
                )
                continue

            detected = detect_language_from_specs(specs_value)
            if detected != lang:
                issues.append(
                    {
                        "product_id": product.id,
                        "product_model": get_product_model(product),
                        "product_folder": product.product_folder,
                        "field": field,
                        "issue_type": "language_mismatch",
                        "expected_language": lang,
                        "detected_language": detected,
                    }
                )

    return Product.objects.count(), checked, issues


def main():
    products_total, checked, issues = build_report()

    for item in issues:
        print(format_issue_line(item))

    print(f"products_total={products_total} fields_checked={checked} issues_count={len(issues)}")


class Command(BaseCommand):
    help = "Проверяет язык полей specs_ru/specs_ua/specs_en и выводит ошибки в терминал"

    def handle(self, *args, **options):
        products_total, checked, issues = build_report()

        for item in issues:
            self.stdout.write(format_issue_line(item))

        self.stdout.write(
            f"products_total={products_total} fields_checked={checked} issues_count={len(issues)}"
        )


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tech_site.settings")
    import django

    django.setup()
    main()
