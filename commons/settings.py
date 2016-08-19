# -*- coding: utf-8

from os import environ
from .libs import get_etcd_value, get_extra_domains

DOCKER_BASE_URL = environ.get("CONSOLE_DOCKER_BASE_URL", "docker.lain:2375")
ETCD_AUTHORITY = environ.get("CONSOLE_ETCD_HOST", "etcd.lain:4001")
CALICOCTL_BIN = environ.get("CALICOCTL_BIN", "/externalbin/calicoctl")
RFP_BIN = environ.get("RFP_BIN", "/externalbin/rfpctl")

try:
    DOMAIN = get_etcd_value("/lain/config/domain", ETCD_AUTHORITY)
except:
    DOMAIN = 'example.lain.com'

def extra_domains():
    try:
        return get_extra_domains("/lain/config/extra_domains", ETCD_AUTHORITY)
    except:
        return []

def main_domain():
    domains = extra_domains()
    try:
        return domains[0]
    except:
        return DOMAIN

PRIVATE_REGISTRY = environ.get("CONSOLE_PRIVATE_REGISTRY", "registry.%s" % DOMAIN)
APISERVER = environ.get("CONSOLE_APISERVER", "http://deploy.%s" % DOMAIN)
SERVER_NAME = environ.get("CONSOLE_SERVER_NAME", "console.%s" % DOMAIN)
APPS_ETCD_PREFIX = environ.get("CONSOLE_APPS_ETCD_PREFIX", "/lain/console/apps")
DEBUG = environ.get("CONSOLE_DEBUG", False)

SYSTEM_VOLUMES_ETCD_PREFIX = environ.get("CONSOLE_SYSTEM_VOLUMES_ETCD_PREFIX", "/lain/config/system_volumes")

CONSOLE_API_SCHEME = environ.get("CONSOLE_API_SCHEME", "http")
CONSOLE_NEED_AUTH_ETCD_KEY = environ.get("CONSOLE_NEED_AUTH_ETCD_KEY", "/lain/config/auth/console")

# sso authorith code flow setting
SSO_CLIENT_ID = environ.get("SSO_CLIENT_ID", None)
SSO_CLIENT_SECRET = environ.get("SSO_CLIENT_SECRET", None)
SSO_SERVER_NAME = environ.get("SSO_SERVER_NAME", None)
SSO_GRANT_TYPE = environ.get("SSO_GRANT_TYPE", "authorization_code")
SSO_REDIRECT_URI = environ.get("SSO_REDIRECT_URI", "%s://console.%s/api/v1/authorize/" % (CONSOLE_API_SCHEME, DOMAIN))
CONSOLE_AUTH_COMPLETE_URL = environ.get("CONSOLE_AUTH_COMPLETE_URL", "%s://console.%s/archon/authorize/complete" % (CONSOLE_API_SCHEME, DOMAIN))
# sso group name setting
SSO_GROUP_NAME_PREFIX = environ.get("SSO_GROUP_NAME_PREFIX", "ConsoleApp" + main_domain())
SSO_GROUP_FULLNAME_PREFIX = environ.get("SSO_GROUP_FULLNAME_PREFIX", "Console APP in %s: " % main_domain())

try:
    CALICO_NETWORK = get_etcd_value("/lain/config/calico_network", ETCD_AUTHORITY)
except:
    CALICO_NETWORK = None

HOST_NETWORK_ETCD_KEY = environ.get("CONSOLE_HOST_NETWORK_ETCD_KEY", "/lain/config/node_network")
try:
    NODE_NETWORK = get_etcd_value("/lain/config/node_network", ETCD_AUTHORITY)
except:
    NODE_NETWORK = None

CALICO_RULE_KEY = environ.get("CALICO_RULE_KEY", "/lain/config/calico_default_rule")

try:
    REGISTRY_IP_WHITELIST = get_etcd_value("/lain/config/registry_ip_whitelist", ETCD_AUTHORITY)
except:
    REGISTRY_IP_WHITELIST = ''

AUTH_TYPES = {
    #TODO: may support other types of auth
    'SSO' : 'lain-sso'
}

# common admin group for lain apps in sso
LAIN_ADMIN_NAME = environ.get("CONSOLE_LAIN_ADMIN_NAME", "lain")
LAIN_ADMIN_ROLE = environ.get("CONSOLE_LAIN_ADMIN_ROLE", "admin")

LVAULT_CONFIG_URL = environ.get("LVAULT_CONFIG_URL", "http://lvault.%s/v2/secrets" % DOMAIN)
