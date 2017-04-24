# -*- coding: utf-8

import pytest

from authorize.models import Authorize
from authorize.utils import appname_prefix


def test_verity_app_access():
    groups = [(appname_prefix + "-" + 'foo1').replace('.', '-'),
              (appname_prefix + "-" + 'foo2').replace('.', '-'),
              (appname_prefix + "-" + 'foo3').replace('.', '-')]
    success = Authorize.verify_app_access(groups, 'foo1')
    assert success
    success = Authorize.verify_app_access(groups, 'foo')
    assert not success
    success = Authorize.verify_app_access([], '')
    assert not success
    success = Authorize.verify_app_access([], None)
    assert not success
