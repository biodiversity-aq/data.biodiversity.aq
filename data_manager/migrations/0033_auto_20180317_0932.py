# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-03-17 09:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0032_auto_20180315_0908'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gbifoccurrence',
            name='hexgrid',
        ),
        migrations.AddField(
            model_name='gbifoccurrence',
            name='hexgrid',
            field=models.ManyToManyField(related_name='GBIFOccurrence', to='data_manager.HexGrid'),
        ),
    ]
