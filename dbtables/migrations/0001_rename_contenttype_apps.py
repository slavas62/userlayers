# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def rename_apps(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'contenttype')
    ContentType.objects.filter(app_label__regex=r'ul_\d+').update(app_label='dbtables')

class Migration(migrations.Migration):

    dependencies = [
        ('userlayers', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(rename_apps, migrations.RunPython.noop)
    ]
