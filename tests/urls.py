from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^userlayers/', include('userlayers.urls')),
)
