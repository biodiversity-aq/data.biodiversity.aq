# Generated by Django 2.2.13 on 2020-09-04 05:12

from django.db import migrations


def delete_orphan_project(apps, schema_editor):
    """
    Changes in results returned from GBIF API resulting in a lot of dataset search results harvested that are not
    related to the query. This function delete those entries which actions were not taken.
    """
    Project = apps.get_model('data_manager', 'Project')
    Project.objects.filter(dataset__isnull=True).delete()
    return


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0104_auto_20200710_1022'),
    ]

    operations = [
        migrations.RunPython(delete_orphan_project)
    ]
