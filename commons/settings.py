# -*- coding: utf-8

from os import environ
from .utils import get_etcd_value, get_extra_domains, get_system_volumes

# if not set extra domains, main domain of the cluster will be the default domain,
# or main domain will be the first domain in extra domains list
ETCD_AUTHORITY = environ.get("CONSOLE_ETCD_HOST", "etcd.lain:4001")
DOMAIN = get_etcd_value("/lain/config/domain",
                        ETCD_AUTHORITY, default='example.lain.com')
EXTRA_DOMAINS = get_extra_domains('/lain/config/extra_domains', ETCD_AUTHORITY)
MAIN_DOMAIN = DOMAIN if len(EXTRA_DOMAINS) == 0 else EXTRA_DOMAINS[0]


# relied service url and setting for console
DOCKER_BASE_URL = environ.get("CONSOLE_DOCKER_BASE_URL", "docker.lain:2375")
PRIVATE_REGISTRY = environ.get(
    "CONSOLE_PRIVATE_REGISTRY", "registry.%s" % DOMAIN)
APISERVER = environ.get("CONSOLE_APISERVER", "http://deploy.%s" % DOMAIN)
SERVER_NAME = environ.get("CONSOLE_SERVER_NAME", "console.%s" % MAIN_DOMAIN)
APPS_ETCD_PREFIX = environ.get(
    "CONSOLE_APPS_ETCD_PREFIX", "/lain/console/apps")
DEBUG = environ.get("CONSOLE_DEBUG", False)
SYSTEM_VOLUMES_ETCD_PREFIX = environ.get(
    "CONSOLE_SYSTEM_VOLUMES_ETCD_PREFIX", "/lain/config/system_volumes")
SYSTEM_VOLUMES = get_system_volumes(SYSTEM_VOLUMES_ETCD_PREFIX, ETCD_AUTHORITY)


# console auth related setting
AUTH_TYPES = {'SSO': 'lain-sso'}  # TODO: may support other types of auth
CONSOLE_NEED_AUTH_ETCD_KEY = environ.get(
    "CONSOLE_NEED_AUTH_ETCD_KEY", "/lain/config/auth/console")
# sso authorize code flow setting
CONSOLE_API_SCHEME = environ.get("CONSOLE_API_SCHEME", "http")
SSO_CLIENT_ID = environ.get("SSO_CLIENT_ID", None)
SSO_CLIENT_SECRET = environ.get("SSO_CLIENT_SECRET", None)
SSO_SERVER_NAME = environ.get("SSO_SERVER_NAME", None)
SSO_GRANT_TYPE = environ.get("SSO_GRANT_TYPE", "authorization_code")
SSO_REDIRECT_URI = environ.get(
    "SSO_REDIRECT_URI", "%s://console.%s/api/v1/authorize/" % (CONSOLE_API_SCHEME, MAIN_DOMAIN))
CONSOLE_AUTH_COMPLETE_URL = environ.get(
    "CONSOLE_AUTH_COMPLETE_URL", "%s://console.%s/archon/authorize/complete" % (CONSOLE_API_SCHEME, MAIN_DOMAIN))
# sso group name setting
SSO_GROUP_NAME_PREFIX = environ.get(
    "SSO_GROUP_NAME_PREFIX", "lainapp-%s" % MAIN_DOMAIN)
SSO_GROUP_FULLNAME_PREFIX = environ.get(
    "SSO_GROUP_FULLNAME_PREFIX", "lain app in %s: " % MAIN_DOMAIN)
# common admin group for lain apps in sso
LAIN_ADMIN_NAME = environ.get("CONSOLE_LAIN_ADMIN_NAME", "lain")
LAIN_ADMIN_ROLE = environ.get("CONSOLE_LAIN_ADMIN_ROLE", "admin")


# calico setting
CALICO_NETWORK = get_etcd_value(
    "/lain/config/calico_network", ETCD_AUTHORITY, default=None)
CALICOCTL_BIN = environ.get("CALICOCTL_BIN", "/externalbin/calicoctl")
CALICO_RULE_KEY = environ.get(
    "CALICO_RULE_KEY", "/lain/config/calico_default_rule")


# registry white list setting
REGISTRY_IP_WHITELIST = get_etcd_value(
    "/lain/config/registry_ip_whitelist", ETCD_AUTHORITY, default='')
NODE_NETWORK = get_etcd_value(
    "/lain/config/node_network", ETCD_AUTHORITY, default=None)


# lvault and configs setting
RFP_BIN = environ.get("RFP_BIN", "/externalbin/rfpctl")
LVAULT_CONFIG_URL = environ.get(
    "LVAULT_CONFIG_URL", "http://lvault.%s/v2/secrets" % DOMAIN)
