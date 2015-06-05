from django.conf.urls import patterns, url, include
from .views import TableCreateView
from api import v1_api

urlpatterns = patterns('',
    url(r'^tables/create/$', TableCreateView.as_view(), name='table_create'),
    url(r'^api/', include(v1_api.urls)),
)
