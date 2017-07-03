from django.shortcuts import render, render_to_response
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from django.core import serializers

# Create your views here.
from .models import OpLog
from log import logger

show_items_number = 10

def render_json_response(status_code, view_object_name, view_object, msg, url):
    r = JsonResponse({
        view_object_name: serializers.serialize('json', view_object),
        'msg': msg,
        'url': url
    })
    r.status_code = status_code
    return r


def api_oplogs(request, appname):
    logger.debug(request)
    try:
        oplogs = OpLog.objects.filter(app=appname).order_by('-pk')[:show_items_number]
    except OpLog.DoesNotExist:
        pass
    return render_json_response(200, "oplog", list(oplogs), "", reverse('api_oplogs', kwargs={"appname": appname}))
