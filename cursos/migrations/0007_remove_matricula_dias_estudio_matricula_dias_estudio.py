# Generated by Django 5.1.7 on 2025-03-22 22:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cursos', '0006_alter_diaestudio_curso'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='matricula',
            name='dias_estudio',
        ),
        migrations.AddField(
            model_name='matricula',
            name='dias_estudio',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
