# Generated by Django 2.2.3 on 2020-02-04 08:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0096_remove_gbifoccurrence_row_json'),
    ]

    operations = [
        migrations.RunSQL("DROP INDEX IF EXISTS gbifoccurrence_idx;"),
        migrations.RunSQL("DROP TRIGGER IF EXISTS occ_tsvector_update ON data_manager_gbifoccurrence;")
    ]
