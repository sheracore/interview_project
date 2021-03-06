# Generated by Django 3.2 on 2022-02-21 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kiosks', '0002_alter_auditlog_action'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('device_add', 'Add Device'), ('device_remove', 'Remove Device'), ('device_change', 'Change Device'), ('device_mount', 'Mount Device'), ('device_unmount', 'Unmount Device'), ('user_login', 'User Login'), ('user_create', 'User Create'), ('user_update', 'User Update'), ('user_destroy', 'User Destroy'), ('user_pass_change', 'User Password Change'), ('scan', 'File Scan'), ('settings_create', 'Settings Create'), ('settings_reset', 'Settings Reset'), ('settings_update', 'Settings Update')], max_length=32, verbose_name='action'),
        ),
    ]
