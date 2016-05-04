# -*- coding: utf-8

import pytest

from authorize.models import Authorize
from authorize.utils import group_prefix, appname_prefix
import hashlib

def test_verity_app_access():
	groups = [group_prefix + hashlib.md5(appname_prefix + 'foo1').hexdigest()[0:30], 
        group_prefix + hashlib.md5(appname_prefix + 'foo2').hexdigest()[0:30],
        group_prefix + hashlib.md5(appname_prefix + 'foo3').hexdigest()[0:30]]
	success = Authorize.verify_app_access(groups, 'foo1')
	assert success
	success = Authorize.verify_app_access(groups, 'foo')
	assert not success
	success = Authorize.verify_app_access([], '')
	assert not success
	success = Authorize.verify_app_access([], None)
	assert not success

