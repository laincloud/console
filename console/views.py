# -*- coding: utf-8

import json
from django.shortcuts import render_to_response
from django.http import JsonResponse, HttpResponse
from django.core.urlresolvers import reverse
from apis.views import AppApi, ProcApi, AuthApi, MaintainApi, ResourceApi, StreamrouterApi
from apis.views import is_deployable
from commons.settings import SERVER_NAME, AUTH_TYPES
from functools import wraps


def permission_required(permission=None):
    permissions = {
        'READ': 'read',
        'MAINTAIN': 'maintain'
    }

    def _check_permision(fun):
        def _decorator(request, *args, **kwargs):
            need_auth = AuthApi.need_auth(AUTH_TYPES['SSO'])
            available_groups = []

            if need_auth:
                access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
                valid, username, available_groups = AuthApi.verify_token(
                    access_token)
                if not valid:
                    return render_json_response(401, 'app', None,
                                                "unauthorized : don't have the access to the operation", reverse('api_docs'))
                else:
                    AuthApi.operater = username
                    request.META['LAIN_AUTH_TYPE'] = AUTH_TYPES['SSO']
                    request.META['SSO_GROUPS'] = available_groups
            else:
                AuthApi.operater = "unknown"
                request.META['LAIN_AUTH_TYPE'] = None

            if permission == permissions['MAINTAIN']:
                appname = args[0]
                if not AppApi.check_app_exist(appname):
                    return render_json_response(404, 'app', None,
                                                'app with appname %s not exist, has not been reposited yet' % appname, reverse('api_repos'))
                if need_auth and not AuthApi.verify_app_access(available_groups, appname):
                    return render_json_response(403, 'maintainer', None,
                                                "forbidden : don't have the access to app %s" % appname, reverse('api_docs'))

            return fun(request, *args, **kwargs)
        return wraps(fun)(_decorator)
    return _check_permision


def deployd_required(fun):
    def _check_deployd_status(request, *args, **kwargs):
        if not is_deployable():
            return render_json_response(503, 'app', None,
                                        'deployd is now in maintain state, please wait for a while', reverse('api_apps'))
        return fun(request, *args, **kwargs)
    return wraps(fun)(_check_deployd_status)


def render_json_response(status_code, view_object_name, view_object, msg, url):
    r = JsonResponse({
        view_object_name: view_object,
        'msg': msg,
        'url': url
    })
    r.status_code = status_code
    return r


def api_docs(request):
    json_url = "%s://%s/api/v1/swagger/" % (request.scheme, SERVER_NAME)
    return render_to_response('console/swagger.html', {'json_url': json_url})


def api_swagger(request):
    return render_to_response('console/swagger.j2', {'server_name': SERVER_NAME}, content_type='application/json; charset=utf-8')


def api_authorize(request):
    try:
        code = request.GET['code']
    except Exception:
        return render_json_response(400, 'auth', None, 'invalid request: should be json body with sso code(string)', reverse('api_docs'))
    else:
        success, token_json = AuthApi.get_sso_access_token(code)
        if not success:
            return render_json_response(401, 'auth', None, "unauthorized : don't have the access to console", reverse('api_docs'))
        else:
            return AuthApi.redirect_to_ui(token_json)


def api_authorize_status(request):
    if request.method == 'GET':
        auth_status = AuthApi.get_auth_status(AUTH_TYPES['SSO'])
        return render_json_response(200, 'auth', auth_status, 'get auth status success', reverse("api_authorize_status"))
    else:
        return _invalid_request_method('auth', request.method)


def api_authorize_registry(request):
    success, result = AuthApi.authorize_registry(request)
    if success:
        return JsonResponse({'token': result}, status=200)
    else:
        return HttpResponse(result, content_type="text/plain", status=401)


def api_apps(request):
    if request.method == 'POST':
        try:
            options = json.loads(request.body)
            appname = options['appname']
        except Exception:
            return render_json_response(400, 'app', None, 'invalid request: should be json body with appname(string)', reverse('api_docs'))
        return api_apps_post(request, appname, options)
    if request.method == 'GET':
        return api_apps_get(request)
    else:
        return _invalid_request_method('apps', request.method)


@permission_required('maintain')
@deployd_required
def api_apps_post(request, appname, options):
    access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
    status_code, view_object, msg, url = AppApi.create_app(
        access_token, appname, options)
    return render_json_response(status_code, 'app', view_object, msg, url)


@permission_required('read')
def api_apps_get(request):
    groups = request.META.get('SSO_GROUPS', [])
    open_auth = request.META.get('LAIN_AUTH_TYPE') != None
    options = request.GET
    status_code, view_object, msg, url = AppApi.list_apps(
        open_auth, groups, options)
    return render_json_response(status_code, 'apps', view_object, msg, url)


def api_app(request, appname):
    if request.method == 'GET':
        return api_app_get(request, appname)
    elif request.method == 'DELETE' or request.method == 'PUT':
        return api_app_high_permit(request, appname)
    else:
        return _invalid_request_method('app', request.method)


@permission_required('maintain')
@deployd_required
def api_app_high_permit(request, appname):
    if request.method == 'DELETE':
        status_code, view_object, msg, url = AppApi.delete_app(appname)
        return render_json_response(status_code, 'app', view_object, msg, url)
    elif request.method == 'PUT':
        try:
            options = json.loads(request.body)
        except Exception:
            options = {}
        access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
        status_code, view_object, msg, url = AppApi.update_app(
            access_token, appname, options)
        return render_json_response(status_code, 'app', view_object, msg, url)


@permission_required('maintain')
def api_app_get(request, appname):
    status_code, view_object, msg, url = AppApi.get_app(appname)
    return render_json_response(status_code, 'app', view_object, msg, url)


def api_procs(request, appname):
    if request.method == 'POST':
        return api_procs_post(request, appname)
    if request.method == 'GET':
        return api_procs_get(request, appname)
    else:
        return _invalid_request_method('procs', request.method)


@permission_required('maintain')
@deployd_required
def api_procs_post(request, appname):
    try:
        options = json.loads(request.body)
        procname = options['procname']
    except Exception:
        return render_json_response(400, 'proc', None, 'invalid request: should be json body with procname(string)', reverse('api_docs'))
    status_code, view_object, msg, url = ProcApi.create_app_proc(
        appname, procname, options)
    return render_json_response(status_code, 'proc', view_object, msg, url)


@permission_required('maintain')
def api_procs_get(request, appname):
    status_code, view_object, msg, url = ProcApi.list_app_procs(appname)
    return render_json_response(status_code, 'procs', view_object, msg, url)


def api_proc(request, appname, procname):
    if request.method == 'GET':
        return api_proc_get(request, appname, procname)
    elif request.method == 'DELETE' or request.method == 'PATCH':
        return api_proc_high_permit(request, appname, procname)
    else:
        _invalid_request_method('proc', request.method)


@permission_required('maintain')
@deployd_required
def api_proc_high_permit(request, appname, procname):
    if request.method == 'DELETE':
        status_code, view_object, msg, url = ProcApi.delete_app_proc(
            appname, procname)
        return render_json_response(status_code, 'proc', view_object, msg, url)
    elif request.method == 'PATCH':
        try:
            options = json.loads(request.body)
        except Exception:
            return render_json_response(400, 'proc', None, 'invalid request: should be json body with num_instances(integer) or cpu(integer) or memory(str)', reverse('api_docs'))
        status_code, view_object, msg, url = ProcApi.update_app_proc(
            appname, procname, options)
        return render_json_response(status_code, 'proc', view_object, msg, url)


@permission_required('maintain')
def api_proc_get(request, appname, procname):
    status_code, view_object, msg, url = ProcApi.get_app_proc(
        appname, procname)
    return render_json_response(status_code, 'proc', view_object, msg, url)


def api_repos(request):
    if request.method == 'POST':
        return api_repos_post(request)
    elif request.method == 'GET':
        return api_repos_get(request)
    else:
        return _invalid_request_method('repos', request.method)


@permission_required('read')
def api_repos_post(request):
    try:
        options = json.loads(request.body)
        appname = options['appname']
    except Exception:
        return render_json_response(400, 'repo', None, 'invalid request: should be json body with appname(string)', reverse('api_docs'))
    access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
    status_code, view_object, msg, url = AppApi.create_repo(
        access_token, appname, options)
    return render_json_response(status_code, 'repos', view_object, msg, url)


@permission_required('read')
def api_repos_get(request):
    groups = request.META.get('SSO_GROUPS', [])
    open_auth = request.META.get('LAIN_AUTH_TYPE') != None
    status_code, view_object, msg, url = AppApi.list_repos(open_auth, groups)
    return render_json_response(status_code, 'repos', view_object, msg, url)


def api_repo(request, appname):
    if request.method != 'GET':
        return _invalid_request_method('repo', request.method)
    else:
        return api_repo_get(request, appname)


@permission_required('maintain')
def api_repo_get(request, appname):
    status_code, view_object, msg, url = AppApi.get_repo(appname)
    return render_json_response(status_code, 'repo', view_object, msg, url)


def api_maintainers(request, appname):
    if not AuthApi.need_auth(AUTH_TYPES['SSO']):
        return render_json_response(403, 'maintainer', None, 'maintainer service not provided, try to open console auth first', reverse('api_docs'))
    return api_maintainers_high_permit(request, appname)


@permission_required('maintain')
def api_maintainers_high_permit(request, appname):
    access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
    if request.method == 'POST':
        try:
            options = json.loads(request.body)
            username = options['username']
            role = options['role']
        except Exception:
            return render_json_response(400, 'maintainers', None, 'invalid request: should be json body with username(string) and role(string)', reverse('api_docs'))
        status_code, view_object, msg, url = MaintainApi.add_maintainer(
            access_token, appname, username, role)
        return render_json_response(status_code, 'maintainer', view_object, msg, url)
    elif request.method == 'GET':
        status_code, view_object, msg, url = MaintainApi.get_maintainers(
            access_token, appname)
        return render_json_response(status_code, 'maintainers', view_object, msg, url)
    else:
        return _invalid_request_method('maintainer', request.method)


def api_maintainer(request, appname, username):
    if not AuthApi.need_auth(AUTH_TYPES['SSO']):
        return render_json_response(403, 'maintainer', None, 'maintainer service not provided, try to open console auth first', reverse('api_docs'))
    return api_maintainer_high_permit(request, appname, username)


@permission_required('maintain')
def api_maintainer_high_permit(request, appname, username):
    access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
    if request.method == 'GET':
        status_code, view_object, msg, url = MaintainApi.get_maintainer(
            access_token, appname, username)
        return render_json_response(status_code, 'maintainer', view_object, msg, url)
    elif request.method == 'DELETE':
        status_code, view_object, msg, url = MaintainApi.delete_maintainer(
            access_token, appname, username)
        return render_json_response(status_code, 'maintainer', view_object, msg, url)
    else:
        return _invalid_request_method('maintainer', request.method)


def api_instances(request, resourcename):
    if request.method != 'GET':
        return _invalid_request_method('resource', request.method)
    else:
        return api_instances_get(request, resourcename)


@permission_required('maintain')
def api_instances_get(request, resourcename):
    status_code, view_object, msg, url = ResourceApi.list_resource_instances(
        resourcename)
    return render_json_response(status_code, 'instances', view_object, msg, url)


def api_roles(request, appname):
    if request.method != 'GET':
        return _invalid_request_method('role', request.method)
    else:
        return api_roles_get(request, appname)


@permission_required('maintain')
def api_roles_get(request, appname):
    access_token = request.META.get('HTTP_ACCESS_TOKEN', 'unknown')
    status_code, view_object, msg, url = MaintainApi.get_role(
        appname, access_token=access_token)
    return render_json_response(status_code, 'role', view_object, msg, url)


def api_role(request, appname, username):
    if request.method == 'GET':
        status_code, view_object, msg, url = MaintainApi.get_role(
            appname, username=username)
        return render_json_response(status_code, 'role', view_object, msg, url)
    else:
        return _invalid_request_method('role', request.method)


def api_versions(request, appname):
    if request.method != 'GET':
        return _invalid_request_method('version', request.method)
    else:
        return api_version_get(request, appname)


@permission_required('maintain')
def api_version_get(request, appname):
    status_code, view_object, msg, url = AppApi.get_versions(appname)
    return render_json_response(status_code, 'version', view_object, msg, url)


def _invalid_request_method(object_type, method):
    return render_json_response(405, object_type, None, 'invalid http method %s' % method, reverse('api_docs'))


def api_streamrouter(request):
    if request.method != 'GET':
        return _invalid_request_method('streamrouter', request.method)
    else:
        return api_streamrouter_get(request)


def api_streamrouter_get(request):
    status_code, view_object, msg, url = StreamrouterApi.list_ports()
    return render_json_response(status_code, 'streamrouter', view_object, msg, url)

