# -*- coding: utf-8

import authorize.utils
import authorize.registry
from commons.settings import AUTH_TYPES, LAIN_ADMIN_NAME, LAIN_ADMIN_ROLE
from log import logger


class Authorize:
    """Authorize for each operation."""

    @classmethod
    def need_auth(cls, auth_type):
        return authorize.utils.need_auth(auth_type)

    @classmethod
    def get_sso_access_token(cls, code):
        try:
            response = authorize.utils.get_sso_access_token(code)
            if response.status_code == 200 and response.json()['access_token']:
                return True, response.json()
            else:
                logger.warning("fail get access token : %s" % response.text)
                return False, None
        except Exception, e:
            logger.error(
                'Exception happen when get sso access token: %s' % str(e))
            return False, None

    @classmethod
    def get_jwt_with_appname(cls, appname):
        return authorize.registry.get_jwt_with_appname(appname)

    @classmethod
    def redirect_to_ui(cls, token_json):
        return authorize.utils.redirect_to_ui(token_json)

    @classmethod
    def authorize_registry(cls, request):
        info = authorize.registry.parse_request(request)

        if not authorize.registry.ip_in_whitelist(info.client_ip):
            if not authorize.utils.is_valid_user(info.username, info.password):
                logger.warning("requests from %s, %s not valid" % (
                    info.username, info.password))
                return False, 'the username or password may not be correct.'
            if info.appname:
                succ, role = Group.get_user_role(info.username, info.appname)
                if not succ:
                    logger.warning("requests from %s for %s not valid" % (
                        info.username, info.appname))
                    return False, 'the user has no access to %s' % info.appname

        return True, authorize.registry.get_jwt_with_request_info(info)

    @classmethod
    def verify_token(cls, access_token):
        try:
            response = authorize.utils.get_user_info(access_token)
            if response.status_code == 200:
                return True, response.json()['name'], response.json()['groups']
            else:
                logger.warning("fail verify token : %s" % response.text)
                return False, '', []
        except Exception, e:
            logger.error('Exception happen when verify token: %s' % str(e))
            return False, '', []

    @classmethod
    def get_username(cls, access_token):
        try:
            response = authorize.utils.get_user_info(access_token)
            if response.status_code == 200:
                return response.json()['name']
            else:
                logger.warning("fail get username from token %s : %s" % (
                    access_token, response.text))
                return None
        except Exception, e:
            logger.error(
                'Exception happen when get username from access token: %s' % str(e))
            return None

    @classmethod
    def verify_app_access(cls, groups, appname):
        for group in groups:
            if group == authorize.utils.get_group_name_for_app(appname):
                return True
        return False


class Group(object):
    """Manage the group in sso for each app."""

    @classmethod
    def create_group_for_app(cls, access_token, appname):
        if not Authorize.need_auth(AUTH_TYPES['SSO']):
            return True, "don't need sso auth, no need for create group"
        try:
            response = authorize.utils.create_group_for_app(
                access_token, appname)
            if response.status_code != 201:
                logger.warning("fail create group for app %s : %s" %
                               (appname, response.text))
                return False, "fail create group for app %s : %s" % (appname, response.text)
            else:
                success, msg = Group.add_group_member(access_token, appname,
                                                      LAIN_ADMIN_NAME, LAIN_ADMIN_ROLE, is_lain_admin=True)
                if not success:
                    return False, msg
                return True, "create group for app %s successfully" % appname
        except Exception, e:
            logger.error("Exception create group for app %s : %s" %
                         (appname, str(e)))
            return False, "sso system wrong when creating group for app %s" % appname

    @classmethod
    def create_group_for_resource_instance(cls, access_token, resourcename, instancename):
        if not Authorize.need_auth(AUTH_TYPES['SSO']):
            return True, "don't need sso auth, no need for create group"
        try:
            success, msg = Group.create_group_for_app(
                access_token, instancename)
            if not success:
                return False, msg

            # add the maintainers of resource into instance maintainer group
            success, maintainers = Group.get_group_members(resourcename)
            if not success:
                return False, maintainers
            instance_maintainer = Authorize.get_username(access_token)
            for maintainer in maintainers:
                if maintainer['name'] == instance_maintainer:
                    continue
                success, msg = Group.add_group_member(
                    access_token, instancename, maintainer['name'], maintainer['role'])
                if not success:
                    return False, msg
            return True, 'create resouce instance group successfully.'
        except Exception, e:
            logger.error("Exception create group for resource instance %s : %s " % (
                instancename, str(e)))
            return False, "sso system wrong when creating group for resource instance %s" % instancename

    @classmethod
    def add_group_member(cls, access_token, appname, username, role, is_lain_admin=False):
        try:
            add_group_func = authorize.utils.add_group_member_for_admin if is_lain_admin else \
                authorize.utils.add_group_member
            response = add_group_func(access_token, appname, username, role)
            if response.status_code != 200:
                logger.warning("fail add group member %s to app %s : %s" % (
                    username, appname, response.text))
                return False, "fail add group member %s to app %s : %s" % (
                    username, appname, response.text)
            else:
                return True, 'add group member successfully'
        except Exception, e:
            logger.error('Exception add group member %s to app %s : %s' % (
                username, appname, str(e)))
            return False, "sso system wrong when adding group member %s to app %s" % (
                username, appname)

    @classmethod
    def delete_group_member(cls, access_token, appname, username):
        try:
            response = authorize.utils.delete_group_member(
                access_token, appname, username)
            if response.status_code != 204:
                logger.warning("fail delete group member %s from app %s : %s" % (
                    username, appname, response.text))
                return False, "fail delete group member %s from app %s : %s" % (
                    username, appname, response.text)
            else:
                return True, "delete group member successfully"
        except Exception, e:
            logger.error('Exception delete group member %s from app %s: %s' % (
                username, appname, str(e)))
            return False, "sso system wrong when deleting group member %s from app %s" % (
                username, appname)

    @classmethod
    def get_group_members(cls, appname):
        try:
            response = authorize.utils.get_group_info(appname)
            maintainers = []
            if response.status_code != 200:
                logger.warning("fail get group members for app %s : %s" % (
                    appname, response.text))
                return False, "fail get group members for app %s : %s" % (appname, response.text)
            else:
                members = response.json()['members']
                for member in members:
                    maintainers.append(member)
                return True, maintainers
        except Exception, e:
            logger.error('Exception get group members for app %s: %s' %
                         (appname, str(e)))
            return False, "sso system wrong when getting group member for app %s" % appname

    @classmethod
    def get_user_role(cls, username, appname):
        try:
            response = authorize.utils.get_user_role(username, appname)
            if response.status_code != 200:
                logger.warning("fail get role in group %s for user %s : %s" % (
                    appname, username, response.text))
                return False, None
            else:
                return True, response.json()['role']
        except Exception, e:
            logger.error('Exception get role in group %s for user %s : %s' % (
                appname, username, str(e)))
            return False, None
