# coding: utf-8
from django.apps import AppConfig

class DBTablesConfig(AppConfig):
    name = u'dbtables'
    verbose_name = u'Таблицы пользовательских слоев'
    
    def get_models(self, *args, **kwargs):
        return []
