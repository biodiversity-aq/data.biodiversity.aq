# Generated by Django 2.2.3 on 2020-01-07 14:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0089_auto_20191203_1341'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='download',
            name='task_results',
        ),
    ]
