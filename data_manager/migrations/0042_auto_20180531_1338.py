# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-05-31 13:38
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0041_auto_20180509_1338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='download',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
