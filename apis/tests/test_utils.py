# -*- coding: utf-8

import pytest

from apis.utils import get_meta_version_from_tag


def test_get_meta_version_from_tag():
    assert get_meta_version_from_tag('meta-123-abc') == '123-abc'
    assert get_meta_version_from_tag('release-123-abc') is None
    assert get_meta_version_from_tag(None) is None
    assert get_meta_version_from_tag('') is None
    assert get_meta_version_from_tag('meta-') is None
    assert get_meta_version_from_tag('123-abc') is None
    assert get_meta_version_from_tag('fake-123-abc') is None
    assert get_meta_version_from_tag('fake-123--abc') is None
