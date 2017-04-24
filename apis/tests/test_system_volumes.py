# -*- coding: utf-8

from apis.models import App
from lain_sdk.yaml.parser import DEFAULT_SYSTEM_VOLUMES

HELLO_META = '''
appname: hello

build:
  base: golang
  script:
    - go build -o hello

release:
  dest_base: ubuntu
  copy:
    - src: hello
      dest: /usr/bin/hello
web:
  cmd: /hello
  env:
'''

HELLO_META_VERSION = '1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5'

REGISTRY_META = '''
appname: registry

build:
  base: sunyi00/centos-registry:1.0.0

release:
  script:
    - mkdir -p /var/lib/registry
  dest_base: sunyi00/centos:1.0.0
  copy:
    - src: /go/bin/registry
      dest: /usr/bin/registry
    - src: config.yml
      dest: config.yml

web:
  cmd: registry config.yml
  memory: 128m
  port: 5000

notify:
  slack: "#lain"
'''

REGISTRY_META_VERSION = '1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5'

REGISTRY_SYSTEM_VOLUME = "/var/lib/registry:/var/lib/registry"


def test_Render_system_volumes():
    hello = App()
    hello.appname = 'hello'
    hello.meta_version = HELLO_META_VERSION
    hello.meta = HELLO_META
    conf = hello.app_spec
    for podg in conf.PodGroups:
        for container in podg.Pod.Containers:
            assert container.SystemVolumes == DEFAULT_SYSTEM_VOLUMES


def test_Render_system_volumes_registry(system_volumes):
    system_volumes.return_value = [REGISTRY_SYSTEM_VOLUME]
    registry = App()
    registry.appname = 'registry'
    registry.meta_version = REGISTRY_META_VERSION
    registry.meta = REGISTRY_META
    conf = registry.app_spec
    for podg in conf.PodGroups:
        for container in podg.Pod.Containers:
            assert container.SystemVolumes == DEFAULT_SYSTEM_VOLUMES + \
                [REGISTRY_SYSTEM_VOLUME]
