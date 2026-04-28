import django.db.models.deletion
from django.db import migrations, models


def populate_breakdown_groups(apps, schema_editor):
    Breakdown = apps.get_model('catalog', 'Breakdown')
    BreakdownGroup = apps.get_model('catalog', 'BreakdownGroup')

    for breakdown in Breakdown.objects.select_related('category', 'brand').all():
        if not breakdown.category_id or not breakdown.brand_id:
            continue

        group_name = f'{breakdown.category.name_ru} {breakdown.brand.name}'.strip()
        breakdown_group, _ = BreakdownGroup.objects.get_or_create(
            category_id=breakdown.category_id,
            brand_id=breakdown.brand_id,
            name=group_name,
        )
        breakdown.breakdown_group_id = breakdown_group.id
        breakdown.save(update_fields=['breakdown_group'])


def restore_breakdown_category_brand(apps, schema_editor):
    Breakdown = apps.get_model('catalog', 'Breakdown')

    for breakdown in Breakdown.objects.select_related('breakdown_group').all():
        if not breakdown.breakdown_group_id:
            continue
        breakdown.category_id = breakdown.breakdown_group.category_id
        breakdown.brand_id = breakdown.breakdown_group.brand_id
        breakdown.save(update_fields=['category', 'brand'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_breakdown'),
    ]

    operations = [
        migrations.CreateModel(
            name='BreakdownGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Группа поломок')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='breakdown_groups', to='catalog.vacuumbrand', verbose_name='Бренд')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='breakdown_groups', to='catalog.category', verbose_name='Тип техники')),
            ],
            options={
                'verbose_name': 'Группа поломок',
                'verbose_name_plural': 'Группы поломок',
                'ordering': ['category__name_ru', 'brand__name', 'name'],
                'constraints': [models.UniqueConstraint(fields=('category', 'brand', 'name'), name='catalog_breakdowngroup_category_brand_name_uniq')],
            },
        ),
        migrations.AddField(
            model_name='product',
            name='breakdown_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='catalog.breakdowngroup', verbose_name='Группа поломок'),
        ),
        migrations.AddField(
            model_name='breakdown',
            name='breakdown_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='breakdowns', to='catalog.breakdowngroup', verbose_name='Группа поломок'),
        ),
        migrations.RunPython(populate_breakdown_groups, restore_breakdown_category_brand),
        migrations.AlterField(
            model_name='breakdown',
            name='breakdown_group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='breakdowns', to='catalog.breakdowngroup', verbose_name='Группа поломок'),
        ),
        migrations.RemoveField(
            model_name='breakdown',
            name='brand',
        ),
        migrations.RemoveField(
            model_name='breakdown',
            name='category',
        ),
        migrations.AlterModelOptions(
            name='breakdown',
            options={'ordering': ['breakdown_group__name', 'title'], 'verbose_name': 'Поломка', 'verbose_name_plural': 'Поломки'},
        ),
    ]
