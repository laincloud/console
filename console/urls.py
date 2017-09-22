from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from django.views.generic import RedirectView

urlpatterns = [

    url(r'^$', RedirectView.as_view(pattern_name='api_docs'), name='console_index'),
    url(r'^(?:api/)?v1/docs/$', 'console.views.api_docs', name='api_docs'),
    url(r'^(?:api/)?v1/swagger/$', 'console.views.api_swagger', name='api_swagger'),

    # app related service
    url(r'^(?:api/)?v1/apps/$', 'console.views.api_apps', name='api_apps'),
    url(r'^(?:api/)?v1/apps/(?P<appname>[^/]+)/$',
        'console.views.api_app', name='api_app'),
    url(r'^(?:api/)?v1/apps/(?P<appname>[^/]+)/procs/$',
        'console.views.api_procs', name='api_procs'),
    url(r'^(?:api/)?v1/apps/(?P<appname>[^/]+)/procs/(?P<procname>[^/]+)/$',
        'console.views.api_proc', name='api_proc'),

    url(r'^(?:api/)?v1/apps/(?P<appname>[^/]+)/proc/(?P<procname>[^/]+)/instance/(?P<instance>[^/]+)/histories/$',
        'console.views.api_proc_history', name='api_proc_history'),

    # authroze service for console ui
    url(r'^(?:api/)?v1/authorize/$',
        'console.views.api_authorize', name='api_authorize'),
    url(r'^(?:api/)?v1/authorize/status/$',
        'console.views.api_authorize_status', name='api_authorize_status'),

    # authorization service for registry
    url(r'^(?:api/)?v1/authorize/registry/$',
        'console.views.api_authorize_registry', name='api_authorize_registry'),

    # repo related service
    url(r'^(?:api/)?v1/repos/$', 'console.views.api_repos', name='api_repos'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/$',
        'console.views.api_repo', name='api_repo'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/maintainers/$',
        'console.views.api_maintainers', name='api_maintainers'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/maintainers/(?P<username>[^/]+)/$',
        'console.views.api_maintainer', name='api_maintainer'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/roles/$',
        'console.views.api_roles', name='api_roles'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/roles/(?P<username>[^/]+)/$',
        'console.views.api_role', name='api_role'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/versions/$',
        'console.views.api_versions', name='api_versions'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/details/$',
        'console.views.api_details', name='api_details'),
    url(r'^(?:api/)?v1/repos/(?P<appname>[^/]+)/push/$',
        'console.views.api_image_push', name='api_image_push'),

    url(r'^(?:api/)?v1/resources/(?P<resourcename>[^/]+)/instances/$',
        'console.views.api_instances', name='api_instances'),

    url(r'^(?:api/)?v1/usedstreamrouterports',
        'console.views.api_streamrouter', name='api_streamrouter'),

    url(r'^(?:api/)?v1/notify/(?P<notify_type>[^/]+)/$',
        'console.views.api_notify', name='api_notify'),

    url(r'^(?:api/)?v1/oplogs/', include('oplog.urls'))

]

urlpatterns += static('/v1/docs/', document_root=settings.SWAGGER_UI_ROOT)
# FIXME: static url seems not supporting regex
urlpatterns += static('/api/v1/docs/', document_root=settings.SWAGGER_UI_ROOT)
