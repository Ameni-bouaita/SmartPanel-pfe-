# Generated by Django 5.1.6 on 2025-03-14 17:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='campaign',
            name='product',
        ),
    ]
