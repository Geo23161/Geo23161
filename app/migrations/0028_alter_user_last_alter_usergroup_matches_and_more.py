# Generated by Django 4.2.7 on 2024-01-28 19:59

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0027_alter_user_last_usergroup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2024, 1, 28, 19, 59, 32, 539356, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.AlterField(
            model_name='usergroup',
            name='matches',
            field=models.ManyToManyField(blank=True, null=True, related_name='is_matches', to='app.usergroup'),
        ),
        migrations.AlterField(
            model_name='usergroup',
            name='proposeds',
            field=models.ManyToManyField(blank=True, null=True, related_name='is_proposed', to='app.usergroup'),
        ),
    ]
