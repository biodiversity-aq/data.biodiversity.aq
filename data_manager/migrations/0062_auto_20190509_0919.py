# Generated by Django 2.2 on 2019-05-09 09:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0061_auto_20190506_1325'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gbifoccurrence',
            old_name='row_json',
            new_name='row_json_text',
        ),
    ]
