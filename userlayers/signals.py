import django.dispatch

table_created = django.dispatch.Signal(providing_args=['md' ,'uri', 'proxy_uri'])
