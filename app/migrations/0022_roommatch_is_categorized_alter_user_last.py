# Generated by Django 4.2.7 on 2023-12-24 06:53

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_user_exil_post_alter_user_created_at_alter_user_last_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='roommatch',
            name='is_categorized',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 12, 24, 6, 53, 15, 55569, tzinfo=datetime.timezone.utc), null=True),
        ),
    ]
