# Generated by Django 2.2.3 on 2019-09-30 07:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0080_custom_index_for_api'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datatype',
            name='data_type',
            field=models.TextField(help_text='Row type of a Darwin-Core Archive. e.g.: "METADATA", "OCCURRENCE", "SAMPLING-EVENT"', unique=True),
        ),
        migrations.AlterField(
            model_name='harvesteddataset',
            name='recordCount',
            field=models.PositiveIntegerField(blank=True, help_text='The number of record associated with the dataset', null=True),
        ),
    ]