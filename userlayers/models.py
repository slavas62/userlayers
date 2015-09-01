# coding: utf-8

from django.db import models
from django.db.models import signals
from django.conf import settings
from mutant.models import ModelDefinition as MD, ModelDefinitionManager as MDManager


class ModelDefinitionManager(MDManager):
    def get_slug_by_name(self, name):
        from .api.naming import translit_and_slugify
        return translit_and_slugify(name)

    def get_by_name(self, name):
        return self.get(name=self.get_slug_by_name(name))


# TODO signals table_create & table_update
class ModelDefinition(MD):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u'владелец')
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=u'дата создания')
    updated_date = models.DateTimeField(auto_now_add=True, auto_now=True, null=True, blank=True,
                                        verbose_name=u'дата обновления')

    objects = ModelDefinitionManager()

    class Meta:
        verbose_name = u'модель'
        verbose_name_plural = u'модели'

    def save(self, *args, **kwargs):
        # TODO optimize import
        # fix crash import
        from .api.naming import get_app_label_for_user, get_db_table_name
        slug = ModelDefinition.objects.get_slug_by_name(self.name)
        self.name = slug[:100]
        if not self.verbose_name:
            self.verbose_name = self.name
        if not self.verbose_name_plural:
            self.verbose_name_plural = self.name
        self.app_label = get_app_label_for_user(self.owner)[:100]
        if not self.db_table:
            table_name = get_db_table_name(self.owner, self.name)[:63]
            self.db_table = table_name
            self.model = table_name
            self.object_name = table_name
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
