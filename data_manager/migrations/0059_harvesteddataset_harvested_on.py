# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2019-01-21 13:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0058_auto_20181031_0914'),
    ]

    operations = [
        migrations.AddField(
            model_name='harvesteddataset',
            name='harvested_on',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
