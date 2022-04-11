# Generated by Django 3.2 on 2022-02-04 20:07

import core.fields
import core.mixins
import core.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('django_celery_beat', '0015_edit_solarschedule_events_choices'),
    ]

    operations = [
        migrations.CreateModel(
            name='Kiosk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('title', core.fields.SafeCharField(blank=True, max_length=64)),
                ('api_ip', core.fields.SafeCharField(max_length=16, validators=[django.core.validators.validate_ipv4_address])),
                ('api_port', models.PositiveIntegerField(default=80)),
                ('api_key', core.fields.SafeCharField(default='changeme', max_length=255)),
                ('ssh_ip', core.fields.SafeCharField(blank=True, max_length=16, null=True, validators=[django.core.validators.validate_ipv4_address])),
                ('ssh_port', models.PositiveSmallIntegerField(null=True)),
                ('ssh_username', core.fields.SafeCharField(blank=True, max_length=64)),
                ('ssh_password', core.fields.SafeCharField(blank=True, max_length=64)),
                ('status', models.JSONField(editable=False, null=True)),
                ('note', core.fields.SafeTextField(blank=True, max_length=4096, null=True)),
                ('serial', core.fields.SafeCharField(max_length=64, unique=True)),
                ('last_update', models.DateTimeField(null=True)),
                ('pt', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='django_celery_beat.periodictask')),
            ],
            options={
                'verbose_name': 'Kiosk',
                'verbose_name_plural': 'Kiosks',
                'permissions': [('remote', 'Can Send Remote Request')],
            },
            bases=(models.Model, core.models.mixins.UpdateModelMixin, core.mixins.AsyncMixin),
        ),
        migrations.CreateModel(
            name='ScanLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.FloatField(null=True)),
                ('md5', models.CharField(max_length=256)),
                ('sha1', models.CharField(max_length=256)),
                ('sha256', models.CharField(max_length=256)),
                ('ext_match', models.BooleanField(null=True)),
                ('extension', models.CharField(max_length=256)),
                ('mimetype', models.CharField(max_length=256)),
                ('username', models.CharField(max_length=32, null=True)),
                ('display_name', models.CharField(max_length=256)),
                ('notes', models.TextField(blank=True)),
                ('status', models.CharField(blank=True, max_length=64)),
                ('valid', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False)),
                ('av_name', core.fields.SafeCharField(max_length=128)),
                ('status_code', models.IntegerField(db_index=True, null=True)),
                ('stdout', models.TextField(blank=True)),
                ('scan_time', models.FloatField(null=True)),
                ('infected_num', models.IntegerField(db_index=True, null=True)),
                ('threats', models.CharField(max_length=512, null=True)),
                ('error', models.TextField(null=True)),
                ('kiosk_title', models.CharField(blank=True, editable=False, max_length=64, null=True)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('scanned_at', models.DateTimeField()),
                ('read', models.BooleanField(default=False, editable=False)),
                ('kiosk', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scan_logs', to='kiosks.kiosk')),
            ],
            options={
                'verbose_name': 'Scan Log',
                'verbose_name_plural': 'Scan Logs',
                'default_permissions': ['view'],
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('device_add', 'Add Device'), ('device_remove', 'Remove Device'), ('device_change', 'Change Device'), ('device_mount', 'Mount Device'), ('device_unmount', 'Unmount Device'), ('user_login', 'User Login'), ('user_create', 'User Create'), ('user_update', 'User Update'), ('user_destroy', 'User Destroy'), ('user_pass_change', 'User Password Change'), ('scan', 'File Scan')], max_length=32, verbose_name='action')),
                ('username', models.CharField(blank=True, max_length=32, null=True)),
                ('remote_addr', models.GenericIPAddressField(blank=True, null=True, verbose_name='remote address')),
                ('additional_data', core.fields.JSONField(blank=True, null=True, verbose_name='additional data')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='object description')),
                ('kiosk_title', models.CharField(blank=True, editable=False, max_length=64, null=True)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('read', models.BooleanField(default=False, editable=False)),
                ('kiosk', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_log', to='kiosks.kiosk')),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'ordering': ['received_at'],
                'default_permissions': ['view'],
            },
        ),
    ]
