# Generated by Django 3.2 on 2022-02-12 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='remote_addr',
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='session',
            name='source',
            field=models.CharField(blank=True, choices=[('upload', 'Upload'), ('url', 'URL'), ('disk', 'Disk'), ('email', 'Email')], max_length=32, null=True),
        ),
    ]
