# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-30 12:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gbifoccurrence',
            name='row_json',
            field=models.TextField(blank=True, null=True),
        ),
    ]
