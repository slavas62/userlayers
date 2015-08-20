from django.db import models
from django.db.models import signals
from django.conf import settings
from mutant.models import ModelDefinition as MD

class ModelDefinition(MD):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)

    def _save_table(self, raw=False, cls=None, force_insert=False, 
        force_update=False, using=None, update_fields=None):
        """
        Hack for sending post_save signals for parent models
        """
        updated = MD._save_table(self, raw=raw, cls=cls, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        signals.post_save.send(sender=cls, instance=self, created=(not updated),
                                   update_fields=update_fields, raw=raw, using=using)

        return updated
    