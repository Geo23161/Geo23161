# Generated by Django 4.2.7 on 2023-12-20 06:08

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0019_alter_niveau_help_dets_alter_user_last'),
    ]

    operations = [
        migrations.AddField(
            model_name='roommatch',
            name='anonymous_obj',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='anonym_history',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 12, 20, 6, 8, 18, 533860, tzinfo=datetime.timezone.utc), null=True),
        ),
    ]
