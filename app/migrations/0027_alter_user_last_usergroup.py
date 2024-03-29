# Generated by Django 4.2.7 on 2024-01-27 19:30

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0026_message_reply_alter_user_last'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2024, 1, 27, 19, 30, 3, 824005, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.CreateModel(
            name='UserGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('code', models.CharField(blank=True, max_length=150, null=True)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='groups_created', to=settings.AUTH_USER_MODEL)),
                ('likes', models.ManyToManyField(related_name='like', to='app.usergroup')),
                ('matches', models.ManyToManyField(related_name='is_matches', to='app.usergroup')),
                ('proposeds', models.ManyToManyField(related_name='is_proposed', to='app.usergroup')),
                ('rooms', models.ManyToManyField(blank=True, null=True, related_name='groups', to='app.roommatch')),
                ('sem_match', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='is_sem_for', to='app.usergroup')),
                ('users', models.ManyToManyField(related_name='my_groups', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
