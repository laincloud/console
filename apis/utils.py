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
from commons.miscs import NoAvailableImages
import commons.utils
from commons.settings import (PRIVATE_REGISTRY, DOCKER_BASE_URL, DEBUG,
                              ETCD_AUTHORITY, CALICO_NETWORK,
                              SYSTEM_VOLUMES, CALICO_RULE_KEY,
                              DOMAIN, EXTRA_DOMAINS)
from log import logger
from .calico import (calico_profile_rule_add)
import pycalico.datastore_datatypes


def read_from_etcd(key):
    return commons.utils.read_from_etcd(key, ETCD_AUTHORITY)


def set_value_to_etcd(key, value):
    return commons.utils.set_value_to_etcd(key, value, ETCD_AUTHORITY)


def delete_from_etcd(key, recursive=False, dir=False):
    return commons.utils.delete_from_etcd(key, ETCD_AUTHORITY, recursive=recursive, dir=dir)


def get_domains():
    return [DOMAIN] + EXTRA_DOMAINS


VALID_TAG_PATERN = re.compile(r"^(meta)-(?P<meta_version>\S+-\S+)$")


def get_meta_version_from_tag(tag):
    if tag is None:
        return None
    x = VALID_TAG_PATERN.match(tag)
    if x:
        return x.group('meta_version')
    else:
        return None


def calico_rule(rule):
    c_rule = pycalico.datastore_datatypes.Rule()
    for k, v in rule.iteritems():
        c_rule[k] = v
    return c_rule


def get_calico_default_rules():
    inbound_rules, outbound_rules = [], []
    try:
        etcd_result = read_from_etcd(CALICO_RULE_KEY)
        calico_rules = json.loads(
            etcd_result.value)  # pylint: disable=no-member
        for rule in calico_rules["outbound_rules"]:
            outbound_rules.append(calico_rule(rule))
        for rule in calico_rules["inbound_rules"]:
            inbound_rules.append(calico_rule(rule))
    except Exception, e:
        logger.error("error parsing calico default rule : %s" % str(e))
        return [], []
    return outbound_rules, inbound_rules


def add_calico_profile_for_app(calico_profile):
    if not docker_network_exists(calico_profile):
        logger.info("ready creating docker network for profile %s" %
                    calico_profile)
        docker_network_add(calico_profile)
        outbound_rules, inbound_rules = get_calico_default_rules()
        for rule in reversed(outbound_rules):
            calico_profile_rule_add(calico_profile, "outbound_rules", rule)
        for rule in reversed(inbound_rules):
            calico_profile_rule_add(calico_profile, "inbound_rules", rule)
        return True
    return False


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
    logger.debug("ready get meta version %s for app %s from registry" %
                 (meta_version, app))
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
        raise Exception("fail get yaml from %s %s: %s" %
                        (app, meta_version, e))
    finally:
        if cli and isinstance(c, dict) and c.get('Id'):
            cli.remove_container(container=c.get('Id'), v=True)
    return y


def shell(cmd):
    retcode = 0
    output = None
    try:
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True)
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
    ipam_pool = create_ipam_pool(subnet=CALICO_NETWORK)
    ipam_config = create_ipam_config(driver="calico-ipam", pool_configs=[ipam_pool])
    result = cli.create_network(name, driver="calico", ipam=ipam_config)
    logger.info("create docker network for app %s : %s" % (name, result))


def docker_network_remove(name):
    cli = get_docker_client(DOCKER_BASE_URL)
    cli.remove_network(name)


def get_system_volumes_from_etcd(appname):
    return SYSTEM_VOLUMES.get(appname, [])


def get_current_time():
    return strftime("%Y-%m-%d %H:%M:%S", gmtime())


def convert_time_from_deployd(d_time):
    c_times = d_time.split("T")
    if len(c_times) <= 1:
        return d_time
    else:
        return "%s %s" % (c_times[0], c_times[1].split('.')[0])
