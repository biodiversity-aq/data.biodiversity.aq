# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-04-18 08:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0035_auto_20180417_0903'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='statistics',
            name='user',
        ),
    ]
