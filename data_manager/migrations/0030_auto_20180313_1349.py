# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-03-13 13:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0029_auto_20180221_1554'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gbifoccurrence',
            name='gbiftaxa',
        ),
        migrations.DeleteModel(
            name='GBIFTaxa',
        ),
    ]
