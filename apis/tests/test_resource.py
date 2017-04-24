# -*- coding: utf-8

from apis.models import Resource, App
from commons.settings import PRIVATE_REGISTRY
import yaml

REDIS_CLIENT_META = '''
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

use_resources:
  redis:
    memory: 128M
    num_instances: 1
    services:
      - redis

web:
  cmd: /hello
  env:
    REDIS_ADDR: redis:3333
'''
REDIS_CLIENT_META_VERSION = '1439365341-06e92b4456116ad5e6875c8c34797d22156d44a5'

REDIS_RESOURCE_META = '''
appname: redis
apptype: resource

build:
  base: golang
  script:
    - go build -o hello

release:
  dest_base: ubuntu
  copy:
    - src: hello
      dest: /usr/bin/hello

service.redis:
  cmd: redis -p 3333
  port: 3333
  num_instances: "{{ num_instances|default(2)|int(2) }}"
  memory: "{{ memory|default('64M') }}"
  portal:
    cmd: ./proxy
'''

REDIS_RESOURCE_META_VERSION = '1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5'


def test_Resource_instance_meta_render():
    hello = App()
    hello.appname = 'hello'
    hello.meta_version = REDIS_CLIENT_META_VERSION
    hello.meta = REDIS_CLIENT_META
    hello_config = hello.lain_config

    redis_resource = App()
    redis_resource.appname = 'redis'
    redis_resource.meta_version = REDIS_RESOURCE_META_VERSION

    meta_from_file = yaml.safe_load(REDIS_RESOURCE_META)
    meta_yaml = yaml.safe_dump(meta_from_file, default_style='"')
    redis_resource.meta = meta_yaml
    redis_instance = App()
    redis_instance.meta_version = REDIS_RESOURCE_META_VERSION
    redis_instance.meta = redis_resource.get_resource_instance_meta(
        'hello', hello_config.use_resources['redis']['context'])
    redis_instance.default_image = \
        "{}/redis:release-{}".format(PRIVATE_REGISTRY,
                                     REDIS_RESOURCE_META_VERSION)
    redis_instance_config = redis_instance.lain_config
    assert redis_instance_config.appname == 'resource.redis.hello'
    assert redis_instance_config.procs[
        'redis'].image == redis_instance.default_image
    assert redis_instance_config.procs['redis'].memory == '128M'
    assert redis_instance_config.procs['redis'].num_instances == 1
    assert redis_instance_config.procs[
        'portal-redis'].image == redis_instance.default_image
