# -*- coding: utf-8

import pytest

from apis.views import ProcApi


@pytest.mark.parametrize("pod, want", [(
    {
        "Containers": [{
            "Id": "1a",
            "Runtime": {
                "Name": "hello",
                "State": {
                    "Running": True,
                    "StartedAt": "2017-02-07T02:26:45.074501152Z"
                },
                "Config": {
                    "Env": ["GOPATH=go"]
                }
            },
            "ContainerIp": "127.0.0.1",
            "ContainerPort": 80,
            "NodeIp": "127.0.0.1"
        }]
    },
    {
        "containerid": "1a",
        "containername": "hello",
        "containerip": "127.0.0.1",
        "containerport": 80,
        "nodeip": "127.0.0.1",
        "status": "True",
        "uptime": "2017-02-07 02:26:45",
        "envs": ["GOPATH=go"]
    })])
def test_ProcApi_render_pod_data(pod, want):
    got = ProcApi.render_pod_data(pod)
    assert got == want


@pytest.mark.parametrize("pod", [
    {
        "Containers": None
    }
])
def test_ProcApi_render_pod_data_with_type_error(pod):
    with pytest.raises(TypeError):
        ProcApi.render_pod_data(pod)


@pytest.mark.parametrize("pod", [
    {
        "Containers": []
    }
])
def test_ProcApi_render_pod_data_with_value_error(pod):
    with pytest.raises(ValueError):
        ProcApi.render_pod_data(pod)
