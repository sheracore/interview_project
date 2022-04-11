# Generated by Django 3.2 on 2022-02-22 11:51

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('kiosks', '0004_rename_auditlog_kioskauditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='kioskauditlog',
            name='level',
            field=models.CharField(default='info', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='kioskauditlog',
            name='message',
            field=models.TextField(default='test'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='kioskauditlog',
            name='time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
