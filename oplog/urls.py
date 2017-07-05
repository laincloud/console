from . import views
from django.conf.urls import url

urlpatterns = [
    url(r'^(?P<appname>[^/]+)/$',
        'oplog.views.api_oplogs', name='api_oplogs'),
]
