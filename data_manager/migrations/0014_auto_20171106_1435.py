# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-11-06 14:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0013_dataset_record_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='person_type_role',
        ),
        migrations.AddField(
            model_name='persontyperole',
            name='person',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='personTypeRole', to='data_manager.Person'),
        ),
    ]
