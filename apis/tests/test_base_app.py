# -*- coding: utf-8

from commons.settings import APPS_ETCD_PREFIX
from apis.base_app import BaseApp
from apis.tests.libs import generate_etcd_app_key_result, generate_etcd_app_dir_result

CONSOLE_ETCD_APP_RESULT_VALUE = '{"meta_version": "1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5", "meta": "appname: console\\nbuild:\\n  base: sunyi00/centos-python:1.0.0\\n  prepare: [touch /sbin/modprobe && chmod +x /sbin/modprobe, pip install -r pip-req.txt,\\n    rm -rf /lain/app/*]\\n  script: [pip install -r pip-req.txt]\\nnotify: {slack: \'#lain\'}\\nweb:\\n  cmd: ./entry.sh\\n  memory: 256m\\n  persistent_dirs: [/externalbin, /lain/app/logs]\\n  port: 8000\\n", "appname": "console", "default_image": "console:1.0.0"}'
WEBROUTER_ETCD_APP_RESULT_VALUE = '{"meta_version": "1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5", "meta": "appname: console\\nbuild:\\n  base: sunyi00/centos-python:1.0.0\\n  prepare: [touch /sbin/modprobe && chmod +x /sbin/modprobe, pip install -r pip-req.txt,\\n    rm -rf /lain/app/*]\\n  script: [pip install -r pip-req.txt]\\nnotify: {slack: \'#lain\'}\\nweb:\\n  cmd: ./entry.sh\\n  memory: 256m\\n  persistent_dirs: [/externalbin, /lain/app/logs]\\n  port: 8000\\n", "appname": "webrouter"}'
REDIS_ETCD_APP_RESULT_VALUE = '{"meta_version": "1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5", "meta": "appname: console\\napptype: resource\\nbuild:\\n  base: sunyi00/centos-python:1.0.0\\n  prepare: [touch /sbin/modprobe && chmod +x /sbin/modprobe, pip install -r pip-req.txt,\\n    rm -rf /lain/app/*]\\n  script: [pip install -r pip-req.txt]\\nnotify: {slack: \'#lain\'}\\nweb:\\n  cmd: ./entry.sh\\n  memory: 256m\\n  persistent_dirs: [/externalbin, /lain/app/logs]\\n  port: 8000\\n", "appname": "redis"}'


def test_BaseApp_create(base_app):
    assert base_app.appname == 'testapp'
    assert base_app.meta_version == ''
    assert base_app.meta == ''
    assert base_app.default_image == ''


def test_BaseApp_get(etcd_operations):
    etcd_operations['read_from_etcd'].return_value = generate_etcd_app_key_result(
        CONSOLE_ETCD_APP_RESULT_VALUE)
    app = BaseApp.get('fake')
    assert app.appname == 'console'
    assert app.meta_version == '1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5'
    assert app.meta == "appname: console\nbuild:\n  base: sunyi00/centos-python:1.0.0\n  prepare: [touch /sbin/modprobe && chmod +x /sbin/modprobe, pip install -r pip-req.txt,\n    rm -rf /lain/app/*]\n  script: [pip install -r pip-req.txt]\nnotify: {slack: '#lain'}\nweb:\n  cmd: ./entry.sh\n  memory: 256m\n  persistent_dirs: [/externalbin, /lain/app/logs]\n  port: 8000\n"
    assert app.default_image == 'console:1.0.0'


def test_BaseApp_all(etcd_operations):
    def side_effect(key):
        if key == BaseApp.ETCD_PREFIX:
            return generate_etcd_app_dir_result({
                '%s/console' % BaseApp.ETCD_PREFIX: CONSOLE_ETCD_APP_RESULT_VALUE,
                '%s/webrouter' % BaseApp.ETCD_PREFIX: WEBROUTER_ETCD_APP_RESULT_VALUE,
            })
        if key == "{}/console".format(BaseApp.ETCD_PREFIX):
            return generate_etcd_app_key_result(CONSOLE_ETCD_APP_RESULT_VALUE)
        if key == "{}/webrouter".format(BaseApp.ETCD_PREFIX):
            return generate_etcd_app_key_result(WEBROUTER_ETCD_APP_RESULT_VALUE)
    etcd_operations['read_from_etcd'].side_effect = side_effect
    apps = BaseApp.all()
    assert len(apps) == 2


def test_BaseApp_etcdkey(base_app):
    assert base_app.appname == 'testapp'
    assert base_app.etcd_key == "{}/testapp".format(BaseApp.ETCD_PREFIX)


def test_BaseApp_available_meta_versions(images_in_registry, base_app):
    assert base_app.availabe_meta_versions() == [
        "1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5",
        "1439341249-fb307c4f8dc1abfac537c94f8bab1e84fc89bcb0",
        "1439338702-67ab21e1b79a391070fb87d85522ab13f79cb664",
        "1438850942-7d603cf23ce7a33551c183a2c66fae0bc8a21131",
    ]


def test_BaseApp_latest_meta_versions(images_in_registry, base_app):
    assert base_app.latest_meta_version == "1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5"
