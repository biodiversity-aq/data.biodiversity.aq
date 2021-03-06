# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-04-25 09:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0037_auto_20180424_0831'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='statistics',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='statistics',
            name='download',
        ),
        migrations.AddField(
            model_name='download',
            name='dataset',
            field=models.ManyToManyField(blank=True, related_name='Download', to='data_manager.Dataset'),
        ),
        migrations.AlterField(
            model_name='download',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='download',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to=''),
        ),
        migrations.DeleteModel(
            name='Statistics',
        ),
    ]
