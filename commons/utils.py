# -*- coding: utf-8

import requests
import tarfile
import yaml
import json
import subprocess
import re
from retrying import retry
from time import gmtime, strftime
from docker import Client
from docker.utils import create_ipam_config, create_ipam_pool
from cStringIO import StringIO
from .miscs import NoAvailableImages
from .libs import get_etcd_client, retry_if_etcd_error
from .settings import (PRIVATE_REGISTRY, DOCKER_BASE_URL,
                       ETCD_AUTHORITY, CALICOCTL_BIN, CALICO_NETWORK,
                       HOST_NETWORK_ETCD_KEY, DEBUG, 
                       SYSTEM_VOLUMES_ETCD_PREFIX, CALICO_RULE_KEY)
from log import logger


@retry(wait_fixed=200, stop_max_attempt_number=3, retry_on_exception=retry_if_etcd_error)
def read_from_etcd(key):
    client = get_etcd_client(ETCD_AUTHORITY)
    return client.read(key)


@retry(wait_fixed=200, stop_max_attempt_number=3, retry_on_exception=retry_if_etcd_error)
def set_value_to_etcd(key, value):
    client = get_etcd_client(ETCD_AUTHORITY)
    return client.write(key, value)


@retry(wait_fixed=200, stop_max_attempt_number=3, retry_on_exception=retry_if_etcd_error)
def delete_from_etcd(key, recursive=False, dir=False):
    client = get_etcd_client(ETCD_AUTHORITY)
    return client.delete(key, recursive=recursive, dir=dir)


VALID_TAG_PATERN = re.compile(r"^(meta)-(?P<meta_version>\S+-\S+)$")


def get_meta_version_from_tag(tag):
    if tag is None:
        return None
    x = VALID_TAG_PATERN.match(tag)
    if x:
        return x.group('meta_version')
    else:
        return None

def get_calico_default_rules():
    inbound_rules, outbound_rules = [], []
    try:
        etcd_result = read_from_etcd(CALICO_RULE_KEY)
        calico_rules = json.loads(etcd_result.value)  # pylint: disable=no-member
        for rule in calico_rules["outbound"]:
            outbound_rules.append(rule)
        for rule in calico_rules["inbound"]:
            inbound_rules.append(rule)
    except Exception, e:
        logger.error("error parsing calico default rule : %s" % str(e))
        return [], []
    return outbound_rules, inbound_rules


def add_calico_profile_for_app(calico_profile):
    if not docker_network_exists(calico_profile):
        docker_network_add(calico_profile)
        outbound_rules, inbound_rules = get_calico_default_rules()
        for rule in outbound_rules:
            calicoctl_profile_rule_op(calico_profile, "add outbound %s" % rule)
        for rule in inbound_rules:
            calicoctl_profile_rule_op(calico_profile, "add inbound %s" % rule)
        return True
    return False


def get_cluster_host_network(etcd_authority=None, host_network_etcd_key=None):
    if not etcd_authority:
        etcd_authority = ETCD_AUTHORITY
    if not host_network_etcd_key:
        host_network_etcd_key = HOST_NETWORK_ETCD_KEY
    cluster_host_network = "%s.%s.0.0/16" % tuple(etcd_authority.split(".")[:2])
    try:
        cluster_host_network_etcd = read_from_etcd(host_network_etcd_key)
        if not cluster_host_network_etcd.dir:
            cluster_host_network = cluster_host_network_etcd.value  # pylint: disable=E1103
    except Exception, e:
        logger.error("error get cluster host network : %s" % str(e))
    return cluster_host_network


def get_docker_client(docker_base_url):
    return Client(base_url=docker_base_url)


def normalize_meta_version(meta_version):
    return meta_version.replace("meta-", "").replace("build-", "").replace("release-", "")


def gen_image_name(app, meta_version, phase='meta', registry=None):
    if not registry:
        registry = PRIVATE_REGISTRY
    return "%s/%s:%s-%s" % (registry, app, phase, meta_version)


def _is_registry_auth_open(registry=None):
    if not registry:
        registry = PRIVATE_REGISTRY
    url = "http://%s/v2/" % registry
    r = requests.get(url)
    if r.status_code == 401:
        return True
    else:
        return False


def _get_registry_access_header(app, registry):
    if _is_registry_auth_open(registry):
        from authorize.models import Authorize
        
        jwt = Authorize.get_jwt_with_appname(app)
        header = {'Authorization': 'Bearer %s' % jwt}
    else:
        header = ''
    return header


def search_images_from_registry(app, registry=None):
    if not registry:
        registry = PRIVATE_REGISTRY

    url = "http://%s/v2/%s/tags/list" % (registry, app)
    header = _get_registry_access_header(app, registry)
    r = requests.get(url, headers=header)
    if r.status_code != 200:
        raise NoAvailableImages("no images here: %s" % url)
    else:
        return r.json()


def get_meta_from_registry(app, meta_version, registry=None):
    logger.debug("ready get meta version %s for app %s from registry" % (meta_version, app))
    meta_version = normalize_meta_version(meta_version)
    if not registry:
        registry = PRIVATE_REGISTRY
    try:
        y = None
        c = None
        cli = None
        cli = get_docker_client(DOCKER_BASE_URL)
        # TODO check if the image already exits
        cli.pull(
            repository="%s/%s" % (registry, app),
            tag="meta-%s" % (meta_version, ),
            insecure_registry=True
        )
        image = "%s/%s:meta-%s" % (registry, app, meta_version)
        command = '/bin/sleep 0.1'
        c = cli.create_container(image=image, command=command)
        r = cli.copy(container=c.get('Id'), resource='/lain.yaml')
        tar = tarfile.open(fileobj=StringIO(r.data))
        f = tar.extractfile('lain.yaml')
        y = yaml.safe_load(f.read())
    except Exception, e:
        logger.error("fail get yaml from %s %s: %s" % (app, meta_version, e))
        raise Exception("fail get yaml from %s %s: %s" % (app, meta_version, e))
    finally:
        if cli and isinstance(c, dict) and c.get('Id'):
            cli.remove_container(container=c.get('Id'), v=True)
    return y


def shell(cmd):
    retcode = 0
    output = None
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except:
        retcode = 1
    finally:
        return (retcode, output)


class CalicoException(Exception):
    pass


def docker_network_exists(name):
    cli = get_docker_client(DOCKER_BASE_URL)
    if len(cli.networks(names=[name])) == 0:
        return False
    else:
        return True


def docker_network_add(name):
    cli = get_docker_client(DOCKER_BASE_URL)
    ipam_pool =  create_ipam_pool(subnet=CALICO_NETWORK)
    ipam_config = create_ipam_config(driver="calico", pool_configs=[ipam_pool])
    cli.create_network(name, driver="calico", ipam=ipam_config)


def docker_network_remove(name):
    cli = get_docker_client(DOCKER_BASE_URL)
    cli.remove_network(name)


def _calicoctl_profile(command, profile):
    cmd = "DOCKER_HOST=%s ETCD_AUTHORITY=%s %s profile %s %s" % (
        DOCKER_BASE_URL,
        ETCD_AUTHORITY,
        CALICOCTL_BIN,
        command,
        profile
    )
    return_code = subprocess.call(cmd, shell=True)
    if DEBUG or return_code == 0:
        return "CALICO PROFILE %s %s : SUCCESS" % (profile, command)
    else:
        raise CalicoException("CALICO PROFILE %s %s : FAIL" % (profile, command))


def calicoctl_profile_rule_op(profile, op):
    cmd = "DOCKER_HOST=%s ETCD_AUTHORITY=%s %s profile %s rule %s" % (
        DOCKER_BASE_URL,
        ETCD_AUTHORITY,
        CALICOCTL_BIN,
        profile,
        op
    )
    return_code = subprocess.call(cmd, shell=True)
    if DEBUG or return_code == 0:
        return "CALICO cmd %s : SUCCESS" % (cmd, )
    else:
        raise CalicoException("CALICO cmd %s : FAIL" % (cmd, ))


def get_system_volumes_from_etcd(appname):
    key = "%s/%s" % (SYSTEM_VOLUMES_ETCD_PREFIX, appname)
    try:
        v = read_from_etcd(key).value  # pylint: disable=no-member
        return [] if v == "" else v.split(";")
    except Exception, e:
        return []


def get_current_time():
    return strftime("%Y-%m-%d %H:%M:%S", gmtime())


def convert_time_from_deployd(d_time):
    c_times = d_time.split("T")
    if len(c_times) <= 1:
        return d_time
    else:
        return "%s %s" % (c_times[0], c_times[1].split('.')[0])