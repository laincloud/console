# -*- coding: utf-8 -*-

from os import path
import pytest
from mock import Mock
from apis.base_app import BaseApp

PWD = path.dirname(path.realpath(__file__))


@pytest.fixture
def images_in_registry(monkeypatch):
    import apis.base_app
    monkeypatch.setattr(apis.base_app, 'search_images_from_registry', Mock(return_value={
        "name": "console",
        "tags": ["release-1438850942-7d603cf23ce7a33551c183a2c66fae0bc8a21131", "meta-1438850942-7d603cf23ce7a33551c183a2c66fae0bc8a21131", "meta-1439338702-67ab21e1b79a391070fb87d85522ab13f79cb664", "release-1439338702-67ab21e1b79a391070fb87d85522ab13f79cb664", "meta-1439341249-fb307c4f8dc1abfac537c94f8bab1e84fc89bcb0", "release-1439341249-fb307c4f8dc1abfac537c94f8bab1e84fc89bcb0", "meta-1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5", "release-1439365340-06e92b4456116ad5e6875c8c34797d22156d44a5"]
    }))


@pytest.fixture
def etcd_operations(monkeypatch):
    import apis.base_app
    etcd_operations = {
        'read_from_etcd': Mock(),
        'delete_from_etcd': Mock(),
        'set_value_to_etcd': Mock(),
    }
    monkeypatch.setattr(apis.base_app, 'read_from_etcd',
                        etcd_operations['read_from_etcd'])
    monkeypatch.setattr(apis.base_app, 'delete_from_etcd',
                        etcd_operations['delete_from_etcd'])
    monkeypatch.setattr(apis.base_app, 'set_value_to_etcd',
                        etcd_operations['set_value_to_etcd'])
    return etcd_operations


@pytest.fixture
def system_volumes(monkeypatch):
    import apis.specs
    system_volumes = Mock()
    monkeypatch.setattr(
        apis.specs, 'get_system_volumes_from_etcd', system_volumes)
    return system_volumes


@pytest.fixture
def base_app(etcd_operations, monkeypatch):
    return BaseApp.create('testapp')
