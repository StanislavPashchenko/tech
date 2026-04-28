import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_breakdowngroup_refactor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='breakdowngroup',
            name='brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='breakdown_groups', to='catalog.vacuumbrand', verbose_name='Бренд'),
        ),
    ]
