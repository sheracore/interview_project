# Generated by Django 3.2.12 on 2022-03-16 11:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_auditlog_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='api',
            name='app_mode',
            field=models.CharField(blank=True, choices=[('web', 'Web'), ('screen', 'Screen')], max_length=16),
        ),
    ]
