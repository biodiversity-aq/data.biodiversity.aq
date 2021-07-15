# Generated by Django 2.2.1 on 2019-07-05 11:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0072_merge_20190701_1359'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='coordinatePrecision',
            new_name='raw_coordinatePrecision',
        ),
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='coordinateUncertaintyInMeters',
            new_name='raw_coordinateUncertaintyInMeters',
        ),
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='decimalLatitude',
            new_name='raw_decimalLatitude',
        ),
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='decimalLongitude',
            new_name='raw_decimalLongitude',
        ),
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='depth',
            new_name='raw_depth',
        ),
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='pointRadiusSpatialFit',
            new_name='raw_pointRadiusSpatialFit',
        ),
        migrations.RenameField(
            model_name='gbifverbatimoccurrence',
            old_name='coordinatePrecision',
            new_name='raw_coordinatePrecision',
        ),
        migrations.RenameField(
            model_name='gbifverbatimoccurrence',
            old_name='coordinateUncertaintyInMeters',
            new_name='raw_coordinateUncertaintyInMeters',
        ),
        migrations.RenameField(
            model_name='gbifverbatimoccurrence',
            old_name='decimalLatitude',
            new_name='raw_decimalLatitude',
        ),
        migrations.RenameField(
            model_name='gbifverbatimoccurrence',
            old_name='decimalLongitude',
            new_name='raw_decimalLongitude',
        ),
        migrations.RenameField(
            model_name='gbifverbatimoccurrence',
            old_name='pointRadiusSpatialFit',
            new_name='raw_pointRadiusSpatialFit',
        ),
    ]
