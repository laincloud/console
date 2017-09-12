# coding:utf-8

import re
from log import logger


GITURL_PATTEN = re.compile(
    r'^(http|https)://([\w|\.]+)/([\w|\-|\-]+)/([\w|\-|\_]+)$')


TIME_OUT = 5


def parse_giturl(giturl):
    m = GITURL_PATTEN.match(giturl)
    if m is None:
        return (None, None, None, None)
    return m.groups()


def api_get(session, url, headers=None, params=None):
    try:
        resp = session.request(
            'GET', url, headers=headers, timeout=TIME_OUT, params=params)
    except Exception as e:
        logger.error('request %s failed with error:%s' %
                     (url, str(e)))
        return
    if resp.status_code >= 300 or resp.status_code < 200:
        logger.error('request %s failed with code:%d, info:%s' %
                     (url, resp.status_code, resp.text))
        return
    try:
        return resp.json()
    except Exception as e:
        logger.error('Invalid Response!!')
