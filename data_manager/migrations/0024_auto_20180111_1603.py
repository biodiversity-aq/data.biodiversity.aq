# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-11 16:03
from __future__ import unicode_literals

import data_manager.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0023_auto_20180104_1605'),
    ]

    operations = [
        migrations.AlterField(
            model_name='download',
            name='file',
            field=models.FileField(upload_to=data_manager.models.Download.get_generated_file_dir),
        ),
    ]
