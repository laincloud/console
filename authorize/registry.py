# -*- coding: utf-8

import os
import sys
import jwt
import time
import random
from netaddr import IPNetwork, IPAddress
from commons.settings import DOMAIN, NODE_NETWORK, REGISTRY_IP_WHITELIST, LAIN_ADMIN_NAME
from log import logger


PRV_FILE = "conf/server.key"
PUB_FILE = "conf/server.pem"

HEAD_TYPE = "JWT"
HEAD_ALG = "RS256"
# HEAD_KID is generated based on PUB_FILE, according to registry code
HEAD_KID = "A4TG:6YYF:IFNY:HJ4R:SKIJ:XPSE:E4X2:RZQD:26I6:EM5U:57R2:ESAY"

CLAIMS_ISS = "auth server"  # the iss_name should be the same with it in registry

TOKEN_EXPIRE_SECOND = 30 * 60
RANDOM_MAX_VALUE = sys.maxint

header = {
    "typ": HEAD_TYPE,
    "alg": HEAD_ALG,
    "kid": HEAD_KID
}

claims = {
    "iss": CLAIMS_ISS,
}


class AuthRequestInfo:
    """basic auth info for registry"""

    def __init__(self, request):
        client_ip = self.__parse_client_ip(request)
        username, password = self.__parse_basic_auth(request)
        types, appname, actions = self.__parse_access_info(request)

        self.account = request.GET.get("account")
        self.service = request.GET.get("service")
        self.client_ip = client_ip
        self.username = username
        self.password = password
        self.types = types
        self.appname = appname
        self.actions = actions

    def __parse_client_ip(self, request):
        return request.META.get('HTTP_X_REAL_IP')

    def __parse_basic_auth(self, request):
        basic_auth = request.META.get('HTTP_AUTHORIZATION')
        if basic_auth:
            auth_type, auth_info = basic_auth.split(' ', 1)
            if auth_type.lower() == 'basic':
                auth_info = auth_info.strip().decode('base64')
                username, password = auth_info.split(':', 1)
                return username, password
        return None, None

    def __parse_access_info(self, request):
        scope = request.GET.get("scope")
        if scope:
            parts = scope.split(":")
            types = parts[0]
            appname = parts[1]
            actions = parts[2].split(",")
            return types, appname, actions
        return None, None, None


def parse_request(request):
    try:
        return AuthRequestInfo(request)
    except Exception, e:
        logger.error("prase auth requst error : %s " % str(e))
        raise Exception("prase auth requst error : %s " % str(e))


# if the request ip is included in the registry_ip_whitelist,
# or in the node network of lain, it's in whitelist
def ip_in_whitelist(ip):
    try:
        logger.debug("client ip request for registry auth is %s" % ip)
        white_ips = [x.strip() for x in REGISTRY_IP_WHITELIST.split(',')]
        if ip in white_ips:
            return True
        return IPAddress(ip) in IPNetwork(NODE_NETWORK)
    except Exception, e:
        logger.error(
            "Exception parse registry whitelist for ip %s : %s" % (ip, str(e)))
        return False


def get_jwt_with_appname(appname):
    claims["sub"] = LAIN_ADMIN_NAME
    claims["aud"] = DOMAIN
    claims["access"] = [{
        "type": "repository",
        "name": appname,
        "actions": ["pull", "push"]
    }]
    return _generate_jwt()


def get_jwt_with_request_info(request_info):
    claims["sub"] = request_info.account
    claims["aud"] = request_info.service
    if request_info.appname:
        claims["access"] = [{
            "type": request_info.types,
            "name": request_info.appname,
            "actions": request_info.actions
        }]
    return _generate_jwt()


def _generate_jwt():
    try:
        now = int(time.time())
        claims["iat"] = now
        claims["nbf"] = now - 1
        claims["exp"] = now + TOKEN_EXPIRE_SECOND
        claims["jti"] = str(random.uniform(0, RANDOM_MAX_VALUE))

        dir_path = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(dir_path, PRV_FILE), 'r') as rsa_priv_file:
            key = rsa_priv_file.read()

        encoded = jwt.encode(claims, key, algorithm=HEAD_ALG, headers=header)
        logger.debug(encoded)

        return encoded
    except Exception, e:
        logger.error("Generate JWT for registry wrong : %s" % str(e))
        raise Exception("Generate JWT for registry wrong : %s" % str(e))
