# coding:utf-8


import time
import requests

from commons.settings import GITLAB_TOKEN
from gitlab import GitLabApi
from util import parse_giturl


SUPPORT_GIT_TYPE = {'gitlab': GitLabApi(GITLAB_TOKEN)}
TIMEFORMAT_ISO8601 = '%Y-%m-%dT%H:%M:%S%z'


def fetch_project_commits(giturl, from_timestamp):
    scheme, host, namespace, project = parse_giturl(giturl)
    if scheme is None:
        return
    git_type = host.split('.')[0]
    git_api = SUPPORT_GIT_TYPE.get(git_type, None)
    if git_api is None:
        return
    since = time.strftime(TIMEFORMAT_ISO8601, time.gmtime(from_timestamp+1))
    return git_api.fetch_project_commits(scheme, host, namespace, project, since)
