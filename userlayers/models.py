from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from mutant.models import ModelDefinition
from .files import UuidHashFilenameUploadTo

class UserToTable(models.Model):
    md = models.ForeignKey(ModelDefinition)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        unique_together = ('md', 'user')

attached_file_upload_to = UuidHashFilenameUploadTo('attached_files/')

class AttachedFile(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    print('------------------------------------------------------------------------------------')
    file = models.FileField(upload_to=attached_file_upload_to)
    object = GenericForeignKey()
