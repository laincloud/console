# -*- coding: utf-8

import json
import requests

from commons.settings import WEBROUTER_ABTEST_API

from log import logging

TIMEOUT = 3


class ABTestPolicy:
    '''
    policy in abtest(https://github.com/CNSRE/ABTestingGateway/blob/master/doc/ab%E5%8A%9F%E8%83%BD%E6%8E%A5%E5%8F%A3%E4%BD%BF%E7%94%A8%E4%BB%8B%E7%BB%8D.md)
    '''

    def __init__(self, raw):
        '''
        raw: '{"divtype":"uidsuffix","divdata":[{"suffix":"1","upstream":"beta1"},{"suffix":"2","upstream":"beta2"}]}'
        '''
        self.raw = raw

    def to_dict(self):
        return json.loads(self.raw)


class ABTestPolicyGroup:
    '''
    policy_group in abtest(https://github.com/CNSRE/ABTestingGateway/blob/master/doc/ab%E5%8A%9F%E8%83%BD%E6%8E%A5%E5%8F%A3%E4%BD%BF%E7%94%A8%E4%BB%8B%E7%BB%8D.md)
    '''

    def __init__(self, rules):
        '''
        rules: {"1":{"divtype":"uidappoint","divdata":[{"uidset":[1234,5124],"upstream":"beta1"},{"uidset":[3214,652],"upstream":"beta2"}]},"2":{"divtype":"iprange","divdata":[{"range":{"start":1111,"end":2222},"upstream":"beta1"},{"range":{"start":3333,"end":4444},"upstream":"beta2"}]}}
        '''
        self.rules = rules

    def to_dict(self):
        return self.rules

    def to_json(self):
        return json.dumps(self.rules)

    def is_valid(self):
        '''
        return: ok, error_message
        '''
        params = {'action': 'policygroup_check'}
        r = requests.post(
            WEBROUTER_ABTEST_API,
            params=params,
            data=self.to_json(),
            timeout=TIMEOUT)
        logging.info('>>> r: {}.'.format(r))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        return True, ''


class ABTest:
    '''
    abtest API(https://github.com/CNSRE/ABTestingGateway/blob/master/doc/ab%E5%8A%9F%E8%83%BD%E6%8E%A5%E5%8F%A3%E4%BD%BF%E7%94%A8%E4%BB%8B%E7%BB%8D.md)
    '''

    @classmethod
    def get_policy(self, policy_id):
        '''
        return: ok, Policy/error_message
        '''
        params = {'action': 'policy_get', 'policyid': policy_id}
        r = requests.get(WEBROUTER_ABTEST_API, params=params, timeout=TIMEOUT)
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        return True, ABTestPolicy(r.json()['data'])

    @classmethod
    def add_policy_group(self, abtest_policy_group):
        '''
        abtest_policy_group: ABTestPolicyGroup
        return: ok, policy_group_id/error_message
        '''
        params = {'action': 'policygroup_set'}
        r = requests.post(
            WEBROUTER_ABTEST_API,
            params=params,
            data=abtest_policy_group.to_json(),
            timeout=TIMEOUT)
        logging.info('>>> r.text: {}.'.format(r.text))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        return True, r.json()['data']['groupid']

    @classmethod
    def get_policy_group(self, policy_group_id):
        '''
        return: ok, ABTestPolicyGroup/error_message
        '''
        params = {'action': 'policygroup_get', 'policygroupid': policygroup_id}
        r = requests.post(WEBROUTER_ABTEST_API, params=params, timeout=TIMEOUT)
        logging.info('>>> r: {}.'.format(r))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        policys = []
        for policy_id in r.json['data']['group']:
            ok, policy_or_err = self.get_policy(policy_id)
            if not ok:
                return False, policy_or_err
            policys.append(policy)

        return True, ABTestPolicyGroup(policys)

    @classmethod
    def delete_policy_group(self, policy_group_id):
        '''
        return: ok, error_message
        '''
        params = {
            'action': 'policygroup_del',
            'policygroupid': policy_group_id
        }
        r = requests.post(WEBROUTER_ABTEST_API, params=params, timeout=TIMEOUT)
        logging.info('>>> r: {}.'.format(r))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        return True, ''

    @classmethod
    def active_mountpoint(self, mountpoint, policy_group_id):
        '''
        mountpoint: for example, a.b.c/d (presume host, i.e, `a.b.c`, is present)
        return: ok, error_message
        '''
        params = {
            'action': 'runtime_set',
            'policygroupid': policy_group_id,
            'hostname': self.__normalize_mountpoint(mountpoint)
        }
        r = requests.post(WEBROUTER_ABTEST_API, params=params, timeout=TIMEOUT)
        logging.info('>>> r: {}.'.format(r))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        return True, ''

    @classmethod
    def deactive_mountpoint(self, mountpoint):
        '''
        mountpoint: for example, a.b.c/d (presume host, i.e, `a.b.c`, is present)
        return: ok, error_message
        '''
        params = {
            'action': 'runtime_del',
            'hostname': self.__normalize_mountpoint(mountpoint)
        }
        r = requests.post(WEBROUTER_ABTEST_API, params=params, timeout=TIMEOUT)
        logging.info('>>> r: {}.'.format(r))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        return True, ''

    @classmethod
    def is_active_mountpoint(self, mountpoint):
        '''
        mountpoint: for example, a.b.c/d (presume host, i.e, `a.b.c`, is present)
        return: ok, error_message
        '''
        params = {
            'action': 'runtime_get',
            'hostname': self.__normalize_mountpoint(mountpoint)
        }
        r = requests.post(WEBROUTER_ABTEST_API, params=params, timeout=TIMEOUT)
        logging.info('>>> r: {}.'.format(r))
        if r.status_code != requests.codes.ok or r.json()['code'] != 200:
            return False, r.json()['desc']

        if r.json()['data']['divsteps'] > 0:
            return True, ''

        return False, ''

    @classmethod
    def __normalize_mountpoint(self, mountpoint):
        '''
        mountpoint: for example, a.b.c/d/e (presume host, i.e, `a.b.c`, is present)
        '''
        mountpoint = mountpoint.rstrip('/')
        mountpoint = mountpoint.replace('/', '.')
        return mountpoint
