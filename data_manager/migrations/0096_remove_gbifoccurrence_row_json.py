# Generated by Django 2.2.3 on 2020-02-04 08:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0095_auto_20200204_0815'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gbifoccurrence',
            name='row_json',
        ),
    ]
