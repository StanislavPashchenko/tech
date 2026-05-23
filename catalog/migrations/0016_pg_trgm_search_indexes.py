from django.db import migrations


PRODUCT_INDEXES = [
    ("catalog_product_product_folder_trgm", "catalog_product", "product_folder"),
    ("catalog_product_name_ru_trgm", "catalog_product", "name_ru"),
    ("catalog_product_name_ua_trgm", "catalog_product", "name_ua"),
    ("catalog_product_name_en_trgm", "catalog_product", "name_en"),
    ("catalog_product_description_ru_trgm", "catalog_product", "description_ru"),
    ("catalog_product_description_ua_trgm", "catalog_product", "description_ua"),
    ("catalog_product_description_en_trgm", "catalog_product", "description_en"),
]

BREAKDOWN_INDEXES = [
    ("catalog_breakdown_title_ru_trgm", "catalog_breakdown", "title"),
    ("catalog_breakdown_title_ua_trgm", "catalog_breakdown", "title_ua"),
    ("catalog_breakdown_title_en_trgm", "catalog_breakdown", "title_en"),
    ("catalog_breakdown_causes_ru_trgm", "catalog_breakdown", "possible_causes"),
    ("catalog_breakdown_causes_ua_trgm", "catalog_breakdown", "possible_causes_ua"),
    ("catalog_breakdown_causes_en_trgm", "catalog_breakdown", "possible_causes_en"),
    ("catalog_breakdown_check_ru_trgm", "catalog_breakdown", "what_to_check"),
    ("catalog_breakdown_check_ua_trgm", "catalog_breakdown", "what_to_check_ua"),
    ("catalog_breakdown_check_en_trgm", "catalog_breakdown", "what_to_check_en"),
    ("catalog_breakdown_fix_ru_trgm", "catalog_breakdown", "how_to_fix"),
    ("catalog_breakdown_fix_ua_trgm", "catalog_breakdown", "how_to_fix_ua"),
    ("catalog_breakdown_fix_en_trgm", "catalog_breakdown", "how_to_fix_en"),
]


def _create_trigram_index(index_name, table_name, column_name):
    return (
        f"CREATE INDEX IF NOT EXISTS {index_name} "
        f"ON {table_name} USING gin ({column_name} gin_trgm_ops);"
    )


def _drop_index(index_name):
    return f"DROP INDEX IF EXISTS {index_name};"


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0015_articleimage_cloudflare_url_alter_articleimage_image"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        *[
            migrations.RunSQL(
                sql=_create_trigram_index(index_name, table_name, column_name),
                reverse_sql=_drop_index(index_name),
            )
            for index_name, table_name, column_name in PRODUCT_INDEXES + BREAKDOWN_INDEXES
        ],
    ]
