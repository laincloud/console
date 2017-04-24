# -*- coding: utf-8

import json
import requests
from django import http
from urllib import urlencode
from urlparse import urlparse, parse_qs
from commons.utils import read_from_etcd
from commons.settings import (ETCD_AUTHORITY, SSO_GROUP_NAME_PREFIX, SSO_GROUP_FULLNAME_PREFIX,
                              SSO_CLIENT_ID, SSO_CLIENT_SECRET, SSO_REDIRECT_URI, SSO_GRANT_TYPE,
                              CONSOLE_AUTH_COMPLETE_URL, CONSOLE_NEED_AUTH_ETCD_KEY)
from log import logger


# parameters for sso auth
appname_prefix = SSO_GROUP_NAME_PREFIX
group_fullname_prefix = SSO_GROUP_FULLNAME_PREFIX
client_id = SSO_CLIENT_ID
client_secret = SSO_CLIENT_SECRET
redirect_uri = SSO_REDIRECT_URI
grant_type = SSO_GRANT_TYPE
console_auth_complete_url = CONSOLE_AUTH_COMPLETE_URL


def send_request(method, path, headers, json, params):
    response = requests.request(
        method, path, headers=headers, json=json, params=params)
    return response


def get_group_name_for_app(appname):
    return (appname_prefix + "-" + appname).replace('.', '-')


def get_group_fullname_for_app(appname):
    return "%s%s" % (group_fullname_prefix, appname)


def need_auth(auth_type):
    etcd_auth_type, _ = _get_auth_msg()
    return auth_type == etcd_auth_type


def _get_sso_server():
    auth_type, auth_url = _get_auth_msg()
    return auth_url


def _get_auth_msg():
    try:
        need_auth_r = read_from_etcd(
            CONSOLE_NEED_AUTH_ETCD_KEY, ETCD_AUTHORITY)
        auth = json.loads(need_auth_r.value)  # pylint: disable=no-member
        return auth['type'], auth['url']
    except Exception:
        return None, None


def get_sso_access_token(code):
    url = "%s/oauth2/token" % _get_sso_server()
    auth_params = {
        'client_id': client_id,
        'grant_type': grant_type,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
    }
    return requests.request("GET", url, headers=None, params=auth_params)


def redirect_to_ui(token_json):
    response = http.HttpResponseRedirect(CONSOLE_AUTH_COMPLETE_URL)
    response.set_cookie('ACCESS_TOKEN', value=token_json[
                        'access_token'], max_age=token_json['expires_in'], httponly=False)
    return response


def get_user_info(access_token):
    url = "%s/api/me/" % _get_sso_server()
    headers = {'Authorization': 'Bearer %s' % access_token}
    return send_request("GET", url, headers, None, None)


def create_group_for_app(access_token, appname):
    group_name = get_group_name_for_app(appname)
    group_fullname = get_group_fullname_for_app(appname)
    group_msg = {'name': group_name, 'fullname': group_fullname}
    headers = {"Content-Type": "application/json",
               "Accept": "application/json", 'Authorization': 'Bearer %s' % access_token}
    url = "%s/api/groups/" % _get_sso_server()
    return send_request("POST", url, headers, group_msg, None)


def add_group_member(access_token, appname, username, role):
    group_name = get_group_name_for_app(appname)
    member_msg = {'role': role}
    headers = {"Content-Type": "application/json",
               "Accept": "application/json", 'Authorization': 'Bearer %s' % access_token}
    url = "%s/api/groups/%s/members/%s" % (
        _get_sso_server(), group_name, username)
    return send_request("PUT", url, headers, member_msg, None)


def add_group_member_for_admin(access_token, appname, username, role):
    group_name = get_group_name_for_app(appname)
    member_msg = {'role': role}
    headers = {"Content-Type": "application/json",
               "Accept": "application/json", 'Authorization': 'Bearer %s' % access_token}
    url = "%s/api/groups/%s/group-members/%s" % (
        _get_sso_server(), group_name, username)
    return send_request("PUT", url, headers, member_msg, None)


def delete_group_member(access_token, appname, username):
    group_name = get_group_name_for_app(appname)
    headers = {"Accept": "application/json",
               'Authorization': 'Bearer %s' % access_token}
    url = "%s/api/groups/%s/members/%s" % (
        _get_sso_server(), group_name, username)
    return send_request("DELETE", url, headers, None, None)


def get_group_info(appname):
    group_name = get_group_name_for_app(appname)
    headers = {"Accept": "application/json"}
    url = "%s/api/groups/%s" % (_get_sso_server(), group_name)
    return send_request("GET", url, headers, None, None)


def get_user_role(username, appname):
    group_name = get_group_name_for_app(appname)
    headers = {"Accept": "application/json"}
    url = "%s/api/groups/%s/members/%s" % (
        _get_sso_server(), group_name, username)
    return send_request("GET", url, headers, None, None)


# FIXME: sso do not provide a specify api to verify one user,
# use the first step of oauth2 temporarily
def is_valid_user(username, password):
    try:
        auth_url = _get_sso_server() + '/oauth2/auth' + '?' + urlencode({
            'client_id': client_id,
            'response_type': 'code',
            'scope': 'write:group',
            'redirect_uri': redirect_uri,
            'state': 'foobar',
        })
        usr_msg = {'login': username, 'password': password}
        result = requests.post(
            auth_url,
            data=usr_msg,
            allow_redirects=False)
        code_callback_url = result.headers['Location']
        authentication = parse_qs(urlparse(code_callback_url).query)
        return authentication['code'][0] != ''
    except Exception, e:
        logger.warning(
            "failed checking user's username and password: %s" % str(e))
        return False
