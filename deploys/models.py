# -*- coding: utf-8

import deploys.utils

DEPLOYD_WORKING_STATUS = 'started'


class Deploy:
    name = ''
    apiserver = ''

    @classmethod
    def create(cls, apiserver, name='default'):
        d = Deploy()
        d.name = name
        d.apiserver = apiserver
        return d

    def is_deployable(self):
        response = deploys.utils.get_deployd_status(self.apiserver)
        if response.status_code == 200 and response.json()['status'] == DEPLOYD_WORKING_STATUS:
            return True
        return False

    def create_podgroup(self, podgroup_json):
        return deploys.utils.create_podgroup(podgroup_json, self.apiserver)

    def get_podgroup(self, podgroup_name):
        return deploys.utils.get_podgroup(podgroup_name, self.apiserver)

    def remove_podgroup(self, podgroup_name):
        return deploys.utils.remove_podgroup(podgroup_name, self.apiserver)

    def patch_podgroup_instance(self, podgroup_name, num_instances):
        return deploys.utils.patch_podgroup_instance(podgroup_name, num_instances, self.apiserver)

    def patch_podgroup_spec(self, podgroup_json):
        return deploys.utils.patch_podgroup_spec(podgroup_json, self.apiserver)

    def post_valiad_ports(self, ports):
        return deploys.utils.post_valiad_ports(ports, self.apiserver)

    def create_dependency(self, dependency_pod_json):
        return deploys.utils.create_dependency(dependency_pod_json, self.apiserver)

    def get_dependency(self, dependency_pod_name):
        return deploys.utils.get_dependency(dependency_pod_name, self.apiserver)

    def remove_dependency(self, dependency_pod_name):
        return deploys.utils.remove_dependency(dependency_pod_name, self.apiserver)

    def update_dependency(self, dependency_pod_json):
        return deploys.utils.update_dependency(dependency_pod_json, self.apiserver)

    def get_streamrouter_ports(self):
        return deploys.utils.get_streamrouter_ports(self.apiserver)

    def __unicode__(self):
        return "<%s:%s>" % (self.name, self.apiserver)
