# Generated by Django 3.2.12 on 2022-04-03 05:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0002_remove_agent_pt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='updatefile',
            name='error',
            field=models.TextField(editable=False, null=True),
        ),
    ]