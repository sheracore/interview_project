# Generated by Django 3.2 on 2022-02-04 20:07

import core.fields
import core.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(choices=[('device_add', 'Add Device'), ('device_remove', 'Remove Device'), ('device_change', 'Change Device'), ('device_mount', 'Mount Device'), ('device_unmount', 'Unmount Device'), ('user_login', 'User Login'), ('user_create', 'User Create'), ('user_update', 'User Update'), ('user_destroy', 'User Destroy'), ('user_pass_change', 'User Password Change'), ('scan', 'File Scan')], max_length=32, verbose_name='action')),
                ('username', models.CharField(blank=True, max_length=32, null=True)),
                ('remote_addr', models.GenericIPAddressField(blank=True, null=True, verbose_name='remote address')),
                ('additional_data', core.fields.JSONField(blank=True, null=True, verbose_name='additional data')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='object description')),
                ('logged', models.BooleanField(db_index=True, default=False, editable=False)),
                ('log_error', models.TextField(null=True)),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'ordering': ['created_at'],
                'default_permissions': ['view'],
            },
        ),
        migrations.CreateModel(
            name='MimeTypeCat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', core.fields.SafeCharField(max_length=128, unique=True)),
            ],
            options={
                'verbose_name': 'Mime Type Category',
                'verbose_name_plural': 'Mime Type Categories',
                'default_permissions': [],
            },
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(max_length=1024, upload_to=core.models.video.get_video_upload_path)),
                ('is_active', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Video File',
                'verbose_name_plural': 'Video Files',
            },
        ),
        migrations.CreateModel(
            name='MimeType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', core.fields.SafeCharField(max_length=128, unique=True)),
                ('extensions', core.fields.JSONField(default=[])),
                ('cat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mimetypes', to='core.mimetypecat')),
            ],
            options={
                'verbose_name': 'Mime Type',
                'verbose_name_plural': 'Mime Types',
            },
        ),
        migrations.CreateModel(
            name='API',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('title', core.fields.SafeCharField(blank=True, max_length=256)),
                ('key', models.CharField(editable=False, max_length=256, unique=True)),
                ('allowed_hosts', core.fields.JSONField(default=[])),
                ('owner', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='apis', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Api',
                'verbose_name_plural': 'Apis',
            },
        ),
    ]