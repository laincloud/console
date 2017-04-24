#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '/lain/app')
import requests
from urlparse import urlparse, parse_qs
from urllib import urlencode
import getpass
import optparse
import sys
import hashlib
from commons.settings import MAIN_DOMAIN
from commons.utils import read_from_etcd
from authorize.utils import create_group_for_app, add_group_member, add_group_member_for_admin
from commons.settings import ETCD_AUTHORITY

requests.packages.urllib3.disable_warnings()
client_id = ''
client_secret = ''
redirect_uri = ''
auth_url = ''
sso_url = ''
grant_type = 'authorization_code'
scope = 'write:group'
token_endpoint = ''


def add_login_option(parser):
    parser.add_option('--client_id', default='3',
                      help="Client id get from the sso system "
                           "[default: 3]")
    parser.add_option('--client_secret', default='lain-cli_admin',
                      help="Client id get from the sso system "
                           "[default: lain-cli_admin]")
    parser.add_option('--redirect_uri', default='https://example.com/',
                      help="Redirect uri get from the sso system "
                           "[default: https://example.com/]")
    parser.add_option('--sso_url', default='http://sso.lain.local',
                      help="The sso_url need to be process "
                           "[default: http://sso.lain.local]")


def get_auth_code(username, password):
    try:
        usr_msg = {'login': username, 'password': password}
        result = requests.post(auth_url, data=usr_msg,
                               allow_redirects=False, verify=False)
        code_callback_url = result.headers['Location']
        authentication = parse_qs(urlparse(code_callback_url).query)
        return True, authentication['code'][0]
    except:
        print("Get sso code error, please try again.")
        return False, ''


def get_auth_token(code):
    try:
        auth_msg = {'client_id': client_id, 'grant_type': 'authorization_code',
                    'client_secret': client_secret, 'code': code, 'redirect_uri': redirect_uri}
        result = requests.get(token_endpoint, headers=None,
                              params=auth_msg, verify=False)
        accessinfo = result.json()
        return True, accessinfo['access_token']
    except Exception as e:
        print("Get sso token error: %s" % e)
        return False, ''


def login_lain(options):
    global token_endpoint
    sso_url = options.sso_url
    authorization_endpoint = sso_url + '/oauth2/auth'
    token_endpoint = sso_url + '/oauth2/token'

    global client_id, client_secret, redirect_uri, auth_url
    client_id = options.client_id
    client_secret = options.client_secret
    redirect_uri = options.redirect_uri
    auth_url = authorization_endpoint + '?' + urlencode({
        'client_id': client_id,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': redirect_uri,
        'state': 'foobar',
    })

    username = raw_input('SSO Username:')
    password = getpass.getpass('SSO Password:')
    get_code_success, code = get_auth_code(username, password)
    if get_code_success:
        get_token_success, token = get_auth_token(code)
        if get_token_success:
            return True, token
    return False, ''


def get_console_apps(access_token):
    appnames = []
    try:
        ETCD_PREFIX = 'lain/console/apps'
        apps_root_r = read_from_etcd(ETCD_PREFIX, ETCD_AUTHORITY)
        for l in apps_root_r.leaves:
            appname = l.key[len(ETCD_PREFIX) + 2:]
            appnames.append(appname)
        return appnames
    except Exception as e:
        print("Get console apps error: %s" % e)
        exit(1)


def get_former_groupname(appname):
    group_prefix = 'ca'
    appname_prefix = "ConsoleApp" + MAIN_DOMAIN
    return "%s%s" % (group_prefix, hashlib.md5(
        appname_prefix + appname).hexdigest()[0:30])


def get_former_group_maintainers(group_name, access_token):
    headers = {"Accept": "application/json"}
    url = "%s/api/groups/%s" % (sso_url, group_name)
    response = requests.get(url, headers=headers)
    maintainers = []
    if response.status_code != 200:
        print "fail get group members for group %s : %s" % (group_name, response.text)
    else:
        members = response.json()['members']
        group_members = response.json()['group_members']
        for member in members:
            maintainers.append(member)
        for group_member in group_members:
            group_member['is_group'] = True
            maintainers.append(group_member)
    return maintainers


def update_maintainers(appname, maintainers, access_token):
    success = True
    for maintainer in maintainers:
        add_member_func = add_group_member_for_admin if maintainer.get(
            'is_group', False) else add_group_member
        response = add_member_func(access_token, appname, maintainer[
            'name'], maintainer['role'])
        if response.status_code >= 400:
            print("fail to add maintainer %s to app %s: %s" %
                  (maintainer['name'], appname, response.text))
            success = False
        else:
            print("success add maintainer %s to app %s" %
                  (maintainer['name'], appname))
    return success


def delete_former_group(group_name, access_token):
    headers = {"Content-Type": "application/json",
               "Accept": "application/json", 'Authorization': 'Bearer %s' % access_token}
    url = "%s/api/groups/%s" % (sso_url, group_name)
    requests.delete(url, headers=headers)


def add_new_group(appname, maintainers, access_token):
    response = create_group_for_app(access_token, appname)
    if response.status_code == 201:
        print("successfully create sso group for app %s" % appname)
        return update_maintainers(appname, maintainers, access_token)
    else:
        print("fail to create new group for app %s: %s" %
              (appname, response.text))
        return False


def upgrade_sso_groups(access_token):
    appnames = get_console_apps(access_token)
    for appname in appnames:
        former_group_name = get_former_groupname(appname)
        maintainers = get_former_group_maintainers(
            former_group_name, access_token)
        if add_new_group(appname, maintainers, access_token):
            delete_former_group(former_group_name, access_token)


def main():
    parser = optparse.OptionParser()
    add_login_option(parser)
    options, args = parser.parse_args()

    global sso_url
    sso_url = options.sso_url

    login_success, token = login_lain(options)
    if login_success:
        upgrade_sso_groups(token)


if __name__ == '__main__':
    sys.exit(main())
