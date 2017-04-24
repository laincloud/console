# -*- coding: utf-8

import requests


def send_request(method, path, body, headers):
    return requests.request(method, path, headers=headers, json=body, timeout=10)


def get_deployd_status(apiserver):
    url = "%s/api/status" % apiserver
    return send_request("GET", url, None, None)


def create_podgroup(podgroup_json, apiserver):
    url = "%s/api/podgroups" % apiserver
    headers = {"Content-Type": "application/json"}
    return send_request("POST", url, podgroup_json, headers)


def get_podgroup(podgroup_name, apiserver):
    url = "%s/api/podgroups?name=%s&force_update=false" % (
        apiserver, podgroup_name)
    return send_request("GET", url, None, None)


def remove_podgroup(podgroup_name, apiserver):
    url = "%s/api/podgroups?name=%s" % (apiserver, podgroup_name)
    return send_request("DELETE", url, None, None)


def patch_podgroup_instance(podgroup_name, num_instances, apiserver):
    url = "%s/api/podgroups?name=%s&num_instances=%s&cmd=replica" % (
        apiserver, podgroup_name, num_instances
    )
    return send_request("PATCH", url, None, None)


def patch_podgroup_spec(podgroup_json, apiserver):
    podgroup_name = podgroup_json['Name']
    pod_json = podgroup_json['Pod']
    url = "%s/api/podgroups?name=%s&cmd=spec" % (apiserver, podgroup_name)
    return send_request("PATCH", url, pod_json, None)

# 检测端口是否被占用


def post_valiad_ports(ports, apiserver):
    url = "%s/api/ports?cmd=validate" % (apiserver)
    headers = {"Content-Type": "application/json"}
    return send_request("POST", url, ports, headers)


def create_dependency(dependency_pod_json, apiserver):
    url = "%s/api/depends" % (apiserver, )
    return send_request("POST", url, dependency_pod_json, None)


def get_dependency(dependency_pod_name, apiserver):
    url = "%s/api/depends?name=%s" % (
        apiserver, dependency_pod_name)
    return send_request("GET", url, None, None)


def remove_dependency(dependency_pod_name, apiserver):
    url = "%s/api/depends?name=%s" % (
        apiserver, dependency_pod_name)
    return send_request("DELETE", url, None, None)


def update_dependency(dependency_pod_json, apiserver):
    url = "%s/api/depends" % apiserver
    return send_request("PUT", url, dependency_pod_json, None)

def get_streamrouter_ports(apiserver):
    url = "%s/api/ports" % apiserver
    return send_request("GET", url, None, None)
