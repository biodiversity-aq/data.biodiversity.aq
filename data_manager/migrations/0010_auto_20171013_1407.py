# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-10-13 14:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0009_auto_20171013_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='person_type_role',
            field=models.ManyToManyField(blank=True, related_name='person', to='data_manager.PersonTypeRole'),
        ),
    ]
