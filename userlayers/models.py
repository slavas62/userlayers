from django.db import models, transaction
from django.db.models import signals
from django.conf import settings
from mutant.models import ModelDefinition as MD
from .middleware import get_request


class ModelDefinition(MD):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)

    @transaction.atomic
    def save(self, *args, **kwargs):
        # fix crash import
        from .api.naming import translit_and_slugify, get_app_label_for_user, get_db_table_name
        request = get_request()
        user = request.user
        slug = translit_and_slugify(self.name)
        self.name = slug[:100]
        self.owner = user
        if not self.verbose_name:
            self.verbose_name = self.name
        if not self.verbose_name_plural:
            self.verbose_name_plural = self.name
        self.app_label = get_app_label_for_user(user)[:100]
        self.db_table = get_db_table_name(user, self.name)[:63]
        self.model = slug[:100]
        if not self.object_name:
            self.object_name = slug[:255]
        if self.pk:
            self.model_class(force_create=True)
        return super(ModelDefinition, self).save(*args, **kwargs)

    def _save_table(self, raw=False, cls=None, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        Hack for sending post_save signals for parent models
        """
        updated = MD._save_table(self, raw=raw, cls=cls, force_insert=force_insert, force_update=force_update,
                                 using=using, update_fields=update_fields)
        signals.post_save.send(sender=cls, instance=self, created=(not updated),
                               update_fields=update_fields, raw=raw, using=using)

        return updated
