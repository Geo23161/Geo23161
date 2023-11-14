# Generated by Django 4.2.3 on 2023-10-15 02:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_cat_user_place_user_cats'),
    ]

    operations = [
        migrations.AddField(
            model_name='abon',
            name='status',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.CreateModel(
            name='Verif',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('piece', models.ImageField(upload_to='pieces/')),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(default='pending', max_length=10)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verifs', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trans_id', models.CharField(blank=True, max_length=150, null=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('abn', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='app.abon')),
            ],
        ),
        migrations.AddField(
            model_name='abon',
            name='verif',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='abns', to='app.verif'),
        ),
    ]