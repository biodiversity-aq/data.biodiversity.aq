# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-10-17 08:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0055_auto_20181016_0641'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='abstract',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='citation',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='doi',
            field=models.TextField(blank=True, null=True),
        ),
    ]