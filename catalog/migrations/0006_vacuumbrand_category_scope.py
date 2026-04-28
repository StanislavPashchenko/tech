import django.db.models.deletion

from django.db import migrations, models


def assign_existing_brands_to_cleaners(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    VacuumBrand = apps.get_model('catalog', 'VacuumBrand')

    cleaners_category, _ = Category.objects.get_or_create(
        id_name='cleaners',
        defaults={
            'name_ru': 'Пылесосы',
            'name_ua': 'Пилососи',
            'name_en': 'Vacuum Cleaners',
            'folder': 'last_cleaners',
        },
    )

    VacuumBrand.objects.filter(category__isnull=True).update(category=cleaners_category)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_assign_detected_vacuum_brands'),
    ]

    operations = [
        migrations.AddField(
            model_name='vacuumbrand',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='brands', to='catalog.category'),
        ),
        migrations.RunPython(assign_existing_brands_to_cleaners, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='vacuumbrand',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brands', to='catalog.category'),
        ),
        migrations.AlterField(
            model_name='vacuumbrand',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='vacuumbrand',
            name='slug',
            field=models.SlugField(max_length=255),
        ),
        migrations.AlterModelOptions(
            name='vacuumbrand',
            options={'ordering': ['name'], 'verbose_name': 'Брэнд', 'verbose_name_plural': 'Брэнды'},
        ),
        migrations.AddConstraint(
            model_name='vacuumbrand',
            constraint=models.UniqueConstraint(fields=('category', 'name'), name='catalog_vacuumbrand_category_name_uniq'),
        ),
        migrations.AddConstraint(
            model_name='vacuumbrand',
            constraint=models.UniqueConstraint(fields=('category', 'slug'), name='catalog_vacuumbrand_category_slug_uniq'),
        ),
    ]
