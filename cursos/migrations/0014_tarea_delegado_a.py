# Generated by Django 5.1.7 on 2025-04-11 23:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cursos', '0013_area_tarea'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarea',
            name='delegado_a',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
