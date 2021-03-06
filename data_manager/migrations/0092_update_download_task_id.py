# Generated by Django 2.2.3 on 2020-01-08 07:57

from django.db import migrations


def update_download_task_id(apps, schema_editor):
    """
    The task_id of Download instances was previously the UUID of Celery task ID + ".zip". This function strip ".zip"
    from it so that the status of Celery task can be easily referred to the TaskResult table based on task_id.
    """
    Download = apps.get_model('data_manager', 'Download')
    for download in Download.objects.all():
        new_task_id = download.task_id.strip('.zip')
        download.task_id = new_task_id
        download.save()


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0091_auto_20200108_0753'),
    ]

    operations = [
        migrations.RunPython(update_download_task_id),
    ]
