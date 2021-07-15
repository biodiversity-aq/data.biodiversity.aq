# Generated by Django 2.2.1 on 2019-06-17 07:20

from django.db import migrations, connection


def batch_update(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute("""DROP INDEX IF EXISTS dataset_idx;""")
        cursor.execute("""UPDATE data_manager_dataset SET eml_tsv = to_tsvector('english', eml_text);""")
        cursor.execute("""CREATE INDEX dataset_idx ON data_manager_dataset USING GIN(eml_tsv);""")


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0067_auto_20190617_0712'),
    ]

    operations = [
        migrations.RunPython(batch_update)
    ]