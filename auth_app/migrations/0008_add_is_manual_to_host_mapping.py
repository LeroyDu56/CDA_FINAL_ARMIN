# Generated by Django 4.2.19 on 2025-04-16 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0007_hostcontact_contact_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='hostipmapping',
            name='is_manual',
            field=models.BooleanField(default=False),
        ),
    ]
