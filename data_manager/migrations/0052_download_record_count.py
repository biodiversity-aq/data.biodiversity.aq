# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-09-17 13:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0051_download_query'),
    ]

    operations = [
        migrations.AddField(
            model_name='download',
            name='record_count',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
