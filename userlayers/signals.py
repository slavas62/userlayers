import django.dispatch

table_created = django.dispatch.Signal(providing_args=['user', 'md' ,'uri', 'proxy_uri'])

table_updated = django.dispatch.Signal(providing_args=['user', 'md' ,'uri', 'proxy_uri'])
