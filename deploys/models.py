# -*- coding: utf-8

import deploys.utils


class Deploy:
    name = ''
    apiserver = ''

    @classmethod
    def create(cls, apiserver, name='default'):
        d = Deploy()
        d.name = name
        d.apiserver = apiserver
        return d

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

    def create_dependency(self, dependency_pod_json):
        return deploys.utils.create_dependency(dependency_pod_json, self.apiserver)

    def get_dependency(self, dependency_pod_name):
        return deploys.utils.get_dependency(dependency_pod_name, self.apiserver)

    def remove_dependency(self, dependency_pod_name):
        return deploys.utils.remove_dependency(dependency_pod_name, self.apiserver)

    def update_dependency(self, dependency_pod_json):
        return deploys.utils.update_dependency(dependency_pod_json, self.apiserver)

    def __unicode__(self):
        return "<%s:%s>" % (self.name, self.apiserver)
