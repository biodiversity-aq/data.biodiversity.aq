# Generated by Django 2.2.13 on 2020-06-12 04:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_manager', '0102_auto_20200604_1026'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='created',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='modified',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]