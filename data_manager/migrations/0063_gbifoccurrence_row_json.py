# Generated by Django 2.2 on 2019-05-09 09:19

import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0062_auto_20190509_0919'),
    ]

    operations = [
        migrations.AddField(
            model_name='gbifoccurrence',
            name='row_json',
            field=django.contrib.postgres.search.SearchVectorField(blank=True, null=True),
        ),
    ]
