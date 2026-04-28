from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0009_breakdowngroup_brand_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='breakdown',
            name='title',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Поломка'),
        ),
        migrations.AlterField(
            model_name='breakdown',
            name='possible_causes',
            field=models.TextField(blank=True, default='', verbose_name='Возможные причины'),
        ),
        migrations.AlterField(
            model_name='breakdown',
            name='what_to_check',
            field=models.TextField(blank=True, default='', verbose_name='Что проверить'),
        ),
        migrations.AlterField(
            model_name='breakdown',
            name='how_to_fix',
            field=models.TextField(blank=True, default='', verbose_name='Как исправить'),
        ),
    ]
