# Generated by Django 3.2.11 on 2022-01-21 17:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0005_auto_20220112_0448'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ingredient',
            old_name='ingredient_name',
            new_name='name',
        ),
        migrations.RenameField(
            model_name='ingredient',
            old_name='units',
            new_name='unit',
        ),
        migrations.RenameField(
            model_name='recipe',
            old_name='recipe_name',
            new_name='name',
        ),
    ]
