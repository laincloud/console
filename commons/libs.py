# -*- coding: utf-8

import json
import etcd
from etcd import EtcdException, EtcdKeyNotFound
from retrying import retry

def get_etcd_client(etcd_authority):
    etcd_host_and_port = etcd_authority.split(":")
    if len(etcd_host_and_port) == 2:
        return etcd.Client(host=etcd_host_and_port[0], port=int(etcd_host_and_port[1]))
    elif len(etcd_host_and_port) == 1:
        return etcd.Client(host=etcd_host_and_port[0], port=4001)
    else:
        raise Exception("invalid ETCD_AUTHORITY : %s" % etcd_authority)

def retry_if_etcd_error(exception):
    return isinstance(exception, EtcdException) and (not isinstance(exception, EtcdKeyNotFound))

@retry(wait_fixed=200, stop_max_attempt_number=3, retry_on_exception=retry_if_etcd_error)
def get_etcd_value(key, etcd_authority):
    client = get_etcd_client(etcd_authority)
    return client.read(key).value  # pylint: disable=E1103

@retry(wait_fixed=200, stop_max_attempt_number=3, retry_on_exception=retry_if_etcd_error)
def get_extra_domains(key, etcd_authority):
    client = get_etcd_client(etcd_authority)
    return json.loads(client.read(key).value)  # pylint: disable=E1103
