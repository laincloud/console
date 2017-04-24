# -*- coding: utf-8 -*-

from mock import Mock


def generate_etcd_app_key_result(value):
    result = Mock()
    result.dir = False
    result.value = value
    return result


def generate_etcd_app_dir_result(kvdict):
    d = Mock()
    d.dir = True
    d.leaves = []
    for k, v in kvdict.iteritems():
        r = generate_etcd_app_key_result(v)
        r.key = k
        d.leaves.append(r)
    return d
