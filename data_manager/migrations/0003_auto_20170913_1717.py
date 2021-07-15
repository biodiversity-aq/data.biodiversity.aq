# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-09-13 15:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0002_gbifoccurrence_row_json'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gbifoccurrence',
            name='dataset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='data_manager.Dataset'),
        ),
    ]
