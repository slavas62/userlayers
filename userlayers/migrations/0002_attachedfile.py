# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import userlayers.files


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('userlayers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttachedFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('file', models.FileField(upload_to=userlayers.files.UuidHashFilenameUploadTo(b'attached_files/'))),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
    ]
