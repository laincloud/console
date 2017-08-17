# coding:utf-8

from util import api_get
import requests


class GitLabApi:

    def __init__(self, token):
        self.session = requests.Session()
        self.token = token

    def _fetch_project_id(self, scheme, host, namespace, project):
        project_url = '{scheme}://{host}/api/v4/projects/{namespace}%2F{project}'.format(
            scheme=scheme, host=host, namespace=namespace, project=project)
        headers = {'PRIVATE-TOKEN': self.token}
        project = api_get(self.session, project_url, headers)
        if project is None:
            return
        return project['id']

    def fetch_project_commits(self, scheme, host, namespace, project, since=None, until=None):
        pid = self._fetch_project_id(scheme, host, namespace, project)
        if id is None:
            return
        commits_url = '{scheme}://{host}/api/v4/projects/{pid}/repository/commits'.format(
            scheme=scheme, host=host, pid=pid)
        headers = {'PRIVATE-TOKEN': self.token}
        payload = {}
        if since is not None:
            payload['since'] = since
        if until is not None:
            payload['until'] = until
        commits_detail = api_get(self.session, commits_url,
                          headers=headers, params=payload)
        if commits_detail is None:
            return
        unique_authors = set()
        commits = []
        for commit in commits_detail:
            unique_authors.add(commit['committer_email'])
            commits.append({'id': commit['short_id'], 'message': '%s [%s]' % (
                commit['committer_name'], commit['message'].strip())})
        return list(unique_authors), commits
