from django.db import models
from django.conf import settings
from mutant.models import ModelDefinition

class UserToTable(models.Model):
    md = models.ForeignKey(ModelDefinition)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        unique_together = ('md', 'user')
