# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-04-17 09:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0034_statistics'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statistics',
            name='download',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='data_manager.Download'),
        ),
    ]