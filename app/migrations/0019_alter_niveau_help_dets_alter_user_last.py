# Generated by Django 4.2.7 on 2023-11-15 06:46

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0018_alter_user_last'),
    ]

    operations = [
        migrations.AlterField(
            model_name='niveau',
            name='help_dets',
            field=models.TextField(default='["L\'assistant de conversation", "Il s\'agit d\'une IA dont le principal r\\u00f4le est de vous proposer des sujets de discussions, des questions, des rendez-vous... Plus vous discutez, plus son niveau augmente et plus ils vous raprochent par ses propositions."]'),
        ),
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 15, 6, 45, 56, 850647, tzinfo=datetime.timezone.utc), null=True),
        ),
    ]
