# Generated by Django 4.2.3 on 2023-10-06 06:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_video_audio_details_image_details_message_old_pk_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='niveau',
            name='help_dets',
            field=models.TextField(default='["L\'aventure commence ici", "Plongez dans des discussions de plus en plus profondes \\u00e0 mesure que vous progressez \\u00e0 travers nos niveaux de conversation"]'),
        ),
    ]