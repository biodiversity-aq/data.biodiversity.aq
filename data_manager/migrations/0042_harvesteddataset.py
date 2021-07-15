# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-06-05 09:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0041_auto_20180509_1338'),
    ]

    operations = [
        migrations.CreateModel(
            name='HarvestedDataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hostingOrganizationKey', models.CharField(blank=True, max_length=150, null=True)),
                ('hostingOrganizationTitle', models.CharField(blank=True, max_length=150, null=True)),
                ('key', models.CharField(max_length=150, unique=True)),
                ('license', models.CharField(blank=True, max_length=150, null=True)),
                ('publishingCountry', models.CharField(blank=True, max_length=150, null=True)),
                ('publishingOrganizationKey', models.CharField(blank=True, max_length=150, null=True)),
                ('publishingOrganizationTitle', models.CharField(blank=True, max_length=150, null=True)),
                ('recordCount', models.CharField(blank=True, max_length=150, null=True)),
                ('title', models.CharField(blank=True, max_length=150, null=True)),
                ('type', models.CharField(blank=True, max_length=150, null=True)),
                ('modified', models.CharField(blank=True, max_length=150, null=True)),
                ('include_in_antabif', models.BooleanField()),
                ('import_full_dataset', models.BooleanField()),
            ],
        ),
    ]