# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-10-12 13:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0007_merge_20171011_1545'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='gbiftaxa',
            managers=[
            ],
        ),
        migrations.AlterField(
            model_name='persontyperole',
            name='role',
            field=models.TextField(blank=True, null=True),
        ),
    ]
