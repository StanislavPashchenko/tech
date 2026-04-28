from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('catalog', '0003_seed_vacuum_brands'),
    ]

    operations = [
        migrations.CreateModel(
            name='VacuumBrandsAdminEntry',
            fields=[],
            options={
                'verbose_name': 'Пылесосы',
                'verbose_name_plural': 'Пылесосы',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('catalog.vacuumbrand',),
        ),
    ]
