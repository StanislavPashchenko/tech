from django.core.management.base import BaseCommand, CommandError

from catalog.duplicate_utils import (
    DEFAULT_DUPLICATE_FIELDS,
    collect_product_duplicates,
    count_duplicate_groups,
    count_duplicate_rows,
)


class Command(BaseCommand):
    help = 'Проверяет точные дубли товаров по названиям'

    def add_arguments(self, parser):
        parser.add_argument(
            '--field',
            action='append',
            choices=DEFAULT_DUPLICATE_FIELDS,
            dest='fields',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
        )

    def handle(self, *args, **options):
        fields = options['fields'] or list(DEFAULT_DUPLICATE_FIELDS)
        limit = max(options['limit'], 1)

        duplicates_by_field = collect_product_duplicates(fields=fields)
        duplicate_groups = count_duplicate_groups(duplicates_by_field)
        duplicate_rows = count_duplicate_rows(duplicates_by_field)

        if not duplicate_groups:
            self.stdout.write(self.style.SUCCESS('Дублей товаров не найдено.'))
            return

        self.stdout.write(
            f'Найдено групп дублей: {duplicate_groups}. Записей в дублях: {duplicate_rows}.'
        )

        for field in fields:
            groups = duplicates_by_field[field]
            if not groups:
                self.stdout.write(f'{field}: дублей нет.')
                continue

            self.stdout.write(f'{field}: {len(groups)} групп дублей.')
            for index, group in enumerate(groups[:limit], start=1):
                self.stdout.write(f'  [{index}] {group["value"]} :: {len(group["items"])}')
                for item in group['items']:
                    self.stdout.write(
                        f'      id={item["id"]}, category={item["category"]}, brand={item["brand"]}'
                    )

        raise CommandError('Найдены дубли товаров.')
