# Generated by Django 5.1.7 on 2025-03-28 14:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cursos', '0007_remove_matricula_dias_estudio_matricula_dias_estudio'),
    ]

    operations = [
        migrations.CreateModel(
            name='Evento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cursos.alumno')),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cursos.curso')),
            ],
        ),
    ]
