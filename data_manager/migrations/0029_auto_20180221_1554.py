# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-21 15:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0028_gbifoccurrence_hexgrid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='download',
            name='file',
            field=models.FileField(upload_to=''),
        ),
    ]
