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
            name='Agent',
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
                ('active', models.BooleanField(default=True)),
                ('av_name', core.fields.SafeCharField(max_length=128)),
                ('updating', models.BooleanField(default=False, editable=False)),
                ('pt', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='django_celery_beat.periodictask')),
            ],
            options={
                'verbose_name': 'Agent',
                'verbose_name_plural': 'Agents',
                'permissions': [('view_agent_stats', 'Can view agent stats')],
            },
            bases=(models.Model, core.models.mixins.UpdateModelMixin, core.mixins.AsyncMixin),
        ),
        migrations.CreateModel(
            name='UpdateFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(max_length=1024, upload_to='updates/')),
                ('display_name', models.CharField(editable=False, max_length=256)),
                ('status_code', models.IntegerField(editable=False, null=True)),
                ('error', models.CharField(editable=False, max_length=256, null=True)),
                ('agent', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='updates', to='agents.agent')),
            ],
            options={
                'verbose_name': 'Update File',
                'verbose_name_plural': 'Update Files',
            },
            bases=(models.Model, core.models.mixins.UpdateModelMixin),
        ),
    ]
