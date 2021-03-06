# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-09-22 09:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0005_auto_20170919_1514'),
    ]

    operations = [
        migrations.CreateModel(
            name='GBIFTaxa',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taxonID', models.TextField(blank=True, null=True)),
                ('scientificNameID', models.TextField(blank=True, null=True)),
                ('acceptedNameUsageID', models.TextField(blank=True, null=True)),
                ('parentNameUsageID', models.TextField(blank=True, null=True)),
                ('originalNameUsageID', models.TextField(blank=True, null=True)),
                ('nameAccordingToID', models.TextField(blank=True, null=True)),
                ('namePublishedInID', models.TextField(blank=True, null=True)),
                ('taxonConceptID', models.TextField(blank=True, null=True)),
                ('scientificName', models.TextField(blank=True, db_index=True, null=True, unique=True)),
                ('acceptedNameUsage', models.TextField(blank=True, null=True)),
                ('parentNameUsage', models.TextField(blank=True, null=True)),
                ('originalNameUsage', models.TextField(blank=True, null=True)),
                ('nameAccordingTo', models.TextField(blank=True, null=True)),
                ('namePublishedIn', models.TextField(blank=True, null=True)),
                ('namePublishedInYear', models.TextField(blank=True, null=True)),
                ('higherClassification', models.TextField(blank=True, null=True)),
                ('kingdom', models.TextField(blank=True, null=True)),
                ('phylum', models.TextField(blank=True, null=True)),
                ('_class', models.TextField(blank=True, null=True)),
                ('order', models.TextField(blank=True, null=True)),
                ('family', models.TextField(blank=True, null=True)),
                ('genus', models.TextField(blank=True, null=True)),
                ('subgenus', models.TextField(blank=True, null=True)),
                ('specificEpithet', models.TextField(blank=True, null=True)),
                ('infraspecificEpithet', models.TextField(blank=True, null=True)),
                ('taxonRank', models.TextField(blank=True, null=True)),
                ('verbatimTaxonRank', models.TextField(blank=True, null=True)),
                ('scientificNameAuthorship', models.TextField(blank=True, null=True)),
                ('vernacularName', models.TextField(blank=True, null=True)),
                ('nomenclaturalCode', models.TextField(blank=True, null=True)),
                ('taxonomicStatus', models.TextField(blank=True, null=True)),
                ('nomenclaturalStatus', models.TextField(blank=True, null=True)),
                ('taxonRemarks', models.TextField(blank=True, null=True)),
                ('taxonKey', models.TextField(blank=True, null=True)),
                ('kingdomKey', models.TextField(blank=True, null=True)),
                ('phylumKey', models.TextField(blank=True, null=True)),
                ('classKey', models.TextField(blank=True, null=True)),
                ('orderKey', models.TextField(blank=True, null=True)),
                ('familyKey', models.TextField(blank=True, null=True)),
                ('genusKey', models.TextField(blank=True, null=True)),
                ('subgenusKey', models.TextField(blank=True, null=True)),
                ('speciesKey', models.TextField(blank=True, null=True)),
                ('species', models.TextField(blank=True, null=True)),
                ('genericName', models.TextField(blank=True, null=True)),
                ('typifiedName', models.TextField(blank=True, null=True)),
                ('row_json', models.TextField(blank=True, null=True)),
            ],
            managers=[
                ('object', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name='gbifoccurrence',
            name='gbiftaxa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='data_manager.GBIFTaxa'),
        ),
    ]
