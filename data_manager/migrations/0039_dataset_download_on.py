# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-04-27 14:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0038_auto_20180425_0927'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='download_on',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
