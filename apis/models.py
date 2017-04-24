# -*- coding: utf-8

import json
from deploys.models import Deploy
from lain_sdk.yaml.parser import (
    render_resource_instance_meta,
    resource_instance_name,
    ProcType,
)
from .base_app import (
    BaseApp,
)
from .specs import (
    json_of_spec,
    AppType,
)
from .utils import (
    docker_network_exists,
    docker_network_remove,
    calicoctl_profile_rule_op,
    add_calico_profile_for_app,
    get_domains,
)
from commons.settings import (
    PRIVATE_REGISTRY,
    APISERVER,
    APPS_ETCD_PREFIX,
    MAIN_DOMAIN,
)
from log import logger


default_deploy = Deploy.create(APISERVER)


class App(BaseApp):

    ETCD_PREFIX = APPS_ETCD_PREFIX

    @property
    def default_deploy(self):
        return default_deploy

    @property
    def docker_network(self):
        return self.appname

    @property
    def calico_profile(self):
        return self.appname

    def add_calico_profile(self):
        '''
        - calicoctl profile add self.appname
        - calicoctl profile self.appname rules update (adding allow from admin)
        '''
        if add_calico_profile_for_app(self.calico_profile):
            calicoctl_profile_rule_op(
                self.calico_profile, "add inbound allow from tag lain --at=1")

    def remove_calico_profile(self):
        if docker_network_exists(self.docker_network):
            docker_network_remove(self.docker_network)

    @property
    def app_status(self):
        if self.lain_config is None or self.get_app_type() == AppType.Resource:
            return None
        podgroups, portals = [], []
        last_error = ''
        status = {
            'AppName': self.appname,
            'PodGroups': podgroups,
            'Portals': portals,
            'LastError': last_error,
        }
        for pg in self.app_spec.PodGroups:
            pg_status = self.podgroup_status(pg.Name)
            if pg_status is None:
                podgroups.append(
                    {'Name': pg.Name, 'Status': 'Error getting PodGroup'})
            else:
                last_error = pg_status['Status']['LastError']
                podgroups.append(pg_status)
        for ps in self.app_spec.Portals:
            ps_status = self.dependency_status(ps.Name)
            if ps_status is None:
                portals.append(
                    {'Name': ps.Name, 'Status': 'Error getting Portal'})
            else:
                portals.append(ps_status)
        status['LastError'] = last_error
        return status

    def proc_and_pg_status(self, procname):
        proc = self.lain_config.procs.get(procname, None)
        if proc is None:
            return None, None
        return proc, self.podgroup_status("%s.%s.%s" % (
            self.appname, proc.type.name, proc.name
        ))

    def podgroup_status(self, name):
        for pg in self.app_spec.PodGroups:
            if pg.Name == name:
                r = self.default_deploy.get_podgroup(pg.Name)
                if r.status_code < 400:
                    return {
                        'Name': pg.Name,
                        'Status': r.json()
                    }
                else:
                    logger.warning("fail getting PodGroup: %s" % r.content)
                    return None
        return None

    def dependency_status(self, name):
        r = self.default_deploy.get_dependency(name)
        if r.status_code < 400:
            return {
                'Name': name,
                'Status': r.json()
            }
        else:
            logger.warning("fail getting Dependency: %s" % r.content)
            return None

    def get_resource_instance_meta(self, client_appname, context):
        return render_resource_instance_meta(
            self.appname, self.meta_version, self.meta,
            client_appname, context,
            PRIVATE_REGISTRY, get_domains()
        )

    # Three parts in app updating:
    #   - delete not depended resource;
    #   - deploy new depended resource;
    #   - update the app itself;
    def app_update(self, origin_resources, origin_procs, configed_instances):
        dp_resources_update_results = self.dp_resource_update(
            origin_resources, configed_instances)
        if not dp_resources_update_results.get("OK", False):
            return {
                'OK': False,
                'dp_resources_update_results': dp_resources_update_results,
                'app_update_results': []
            }

        app_update_results = self.basic_app_deploy(origin_procs)
        if app_update_results.get('OK', False):
            self.set_deployed()
        return {
            'OK': app_update_results.get('OK', False),
            'dp_resources_update_results': dp_resources_update_results,
            'app_update_results': app_update_results
        }

    def dp_resource_update(self, origin_resources, configed_instances):
        resources_need_deploy = []
        instances_deploy_results = {}
        instances_remove_results = {}
        dp_resource_update_result = True
        new_resources = self.lain_config.use_resources
        need_deploy_resources = dict.fromkeys(
            [r for r in new_resources if r not in origin_resources])
        need_remove_resources = dict.fromkeys(
            [r for r in origin_resources if r not in new_resources])
        for resourcename in need_deploy_resources.keys():
            need_deploy_resource, deploy_success, instance_deploy_result = \
                self.resource_instance_deploy(resourcename, new_resources[
                                              resourcename], configed_instances)
            if need_deploy_resource:
                resources_need_deploy.append(need_deploy_resource)
                dp_resource_update_result = False
            if not deploy_success:
                dp_resource_update_result = False
            instances_deploy_results[resource_instance_name(
                resourcename, self.appname)] = instance_deploy_result

        if not dp_resource_update_result:
            return {
                'OK': dp_resource_update_result,
                'resources_need_deploy': resources_need_deploy,
                'instances_deploy_results': instances_deploy_results,
                'instances_remove_results': instances_remove_results
            }

        for resourcename in need_remove_resources.keys():
            instancename = resource_instance_name(resourcename, self.appname)
            remove_result = self.resource_instance_remove(instancename)
            if remove_result and not remove_result.get("OK", False):
                dp_resource_update_result = False
            instances_remove_results[instancename] = remove_result

        return {
            'OK': dp_resource_update_result,
            'resources_need_deploy': resources_need_deploy,
            'instances_deploy_results': instances_deploy_results,
            'instances_remove_results': instances_remove_results
        }

    # Two parts in app deploying:
    #   - deploy depended resource instance
    #   - deploy app itself
    def app_deploy(self, configed_instances):
        dp_resources_deploy_results = self.dp_resource_deploy(
            configed_instances)
        if not dp_resources_deploy_results.get("OK", False):
            return {
                'OK': False,
                'dp_resources_deploy_results': dp_resources_deploy_results,
                'app_deploy_results': []
            }

        app_deploy_results = self.basic_app_deploy()
        return {
            'OK': app_deploy_results.get('OK', False),
            'dp_resources_deploy_results': dp_resources_deploy_results,
            'app_deploy_results': app_deploy_results
        }

    def dp_resource_deploy(self, configed_instances):
        resources_need_deploy = []
        instances_deploy_results = {}
        resources = self.lain_config.use_resources
        resource_instance_deploy_result = True
        if not resources:
            return {
                "OK": True,
                'has_resource': False,
                'resources_need_deploy': resources_need_deploy,
                'instances_deploy_results': instances_deploy_results
            }
        for resourcename, resource_props in resources.iteritems():
            need_deploy_resource, deploy_success, instance_deploy_result = \
                self.resource_instance_deploy(
                    resourcename, resource_props, configed_instances)
            if need_deploy_resource:
                resources_need_deploy.append(need_deploy_resource)
            if not deploy_success:
                resource_instance_deploy_result = False
            instances_deploy_results[resource_instance_name(
                resourcename, self.appname)] = instance_deploy_result
        return {
            'OK': resource_instance_deploy_result,
            'has_resource': True,
            'resources_need_deploy': resources_need_deploy,
            'instances_deploy_results': instances_deploy_results
        }

    def resource_instance_deploy(self, resourcename, resource_props, configed_instances):
        instancename = resource_instance_name(resourcename, self.appname)
        resource_instance = configed_instances[instancename]
        resource_instance.update_app_type()
        instance_deploy_result = resource_instance.basic_app_deploy()
        instance_deploy_success = instance_deploy_result.get("OK", False)
        if instance_deploy_success:
            resource_instance.set_deployed()
        return None, instance_deploy_success, instance_deploy_result

    def basic_app_deploy(self, origin_procs=None):
        logger.info("deploy basic app : %s " % self.appname)
        proc_results = {}
        proc_deploy_success = {}
        proc_deploy_failed = {}
        portal_results = {}
        portals_register_success = {}
        portals_register_failed = {}
        portals_update_success = {}
        portals_update_failed = {}
        for pg_spec in self.app_spec.PodGroups:
            pg_result = recursive_deploy(pg_spec)
            if pg_result.get('OK', False):
                proc_deploy_success[pg_spec.Name] = pg_result
            else:
                proc_deploy_failed[pg_spec.Name] = pg_result
        proc_results['OK'] = len(proc_deploy_failed) == 0
        proc_results['proc_deploy_success'] = proc_deploy_success
        proc_results['proc_deploy_failed'] = proc_deploy_failed

        for dp_spec in self.app_spec.Portals:
            portal_proc_name = dp_spec.Name.split(".")[-1]
            for c in dp_spec.Containers:
                c.set_env('LAIN_APPNAME', self.appname)
                c.set_env('LAIN_APP_RELEASE_VERSION', self.meta_version)
                c.set_env('LAIN_PROCNAME', portal_proc_name)
                c.set_env('LAIN_SERVICE_NAME', self.get_service_name_from_portal_name(
                    portal_proc_name))
                c.set_env('LAIN_DOMAIN', MAIN_DOMAIN)
            now_dependency = self.dependency_status(dp_spec.Name)
            if now_dependency:
                portal_r = self.default_deploy.update_dependency(
                    json_of_spec(dp_spec))
                if portal_r.status_code < 400:
                    portals_update_success[dp_spec.Name] = portal_r
                else:
                    portals_update_failed[dp_spec.Name] = portal_r
            else:
                portal_r = self.default_deploy.create_dependency(
                    json_of_spec(dp_spec))
                if portal_r.status_code < 400:
                    portals_register_success[dp_spec.Name] = portal_r
                else:
                    portals_register_failed[dp_spec.Name] = portal_r
        portal_results = {
            'OK': len(portals_register_failed) == 0,
            'portals_register_success': portals_register_success,
            'portals_register_failed': portals_register_failed,
            'portals_update_success': portals_update_success,
            'portals_update_failed': portals_update_failed
        }

        result = {
            'OK': proc_results.get('OK', False) and portal_results.get('OK', False),
            'proc_results': proc_results,
            'portal_results': portal_results
        }
        if origin_procs is not None:
            result['useless_procs_remove_results'] = self.useless_procs_remove(
                origin_procs)

        return result

    def useless_procs_remove(self, origin_procs):
        remove_results = {}
        remove_success_results = {}
        remove_failed_results = {}
        remove_missed_results = {}

        current_pgs = ["%s.%s.%s" % (self.appname, p.type.name, p.name)
                            for p in self.lain_config.procs.values()]
        try:
            for proc in origin_procs:
                pg_name = "%s.%s.%s" % (
                    self.appname, proc.type.name, proc.name)
                if pg_name in current_pgs:
                    continue

                logger.info("remove useless proc %s of app : %s " %
                            (pg_name, self.appname))
                remove_r = self.podgroup_remove(pg_name) if proc.type != ProcType.portal else \
                    self.dependency_remove(pg_name)
                if remove_r.status_code < 400:
                    remove_success_results[pg_name] = remove_r
                elif remove_r.status_code == 404:
                    remove_missed_results[pg_name] = remove_r
                else:
                    remove_failed_results[pg_name] = remove_r
        except Exception, e:
            logger.warning("failed when trying to remove useless proc of app %s: %s" %
                (self.appname, str(e)))
        remove_results = {
            'OK': len(remove_failed_results) == 0,
            'remove_success_results': remove_success_results,
            'remove_failed_results': remove_failed_results,
            'remove_missed_results': remove_missed_results
        }
        return remove_results

    def app_remove(self):
        # remove the app itself first
        app_remove_results = self.basic_app_remove()
        resource_instance_remove_results = {}
        if not app_remove_results.get('OK', False):
            return {
                'OK': False,
                'app_remove_results': app_remove_results,
                'dp_resources_remove_results': {},
            }

        # remove the used resource instances
        resource_instance_remove_results = self.dp_resource_remove()
        return {
            'OK': resource_instance_remove_results.get('OK', False),
            'app_remove_results': app_remove_results,
            'dp_resources_remove_results': resource_instance_remove_results,
        }

    def dp_resource_remove(self):
        resources = self.lain_config.use_resources
        resource_instance_remove_result = True
        instances_remove_results = {}
        if not resources:
            return {
                "OK": True,
                'has_resource': False,
                'instances_remove_results': instances_remove_results
            }
        for resourcename, resource_props in resources.iteritems():
            instancename = resource_instance_name(resourcename, self.appname)
            remove_result = self.resource_instance_remove(instancename)
            if remove_result and not remove_result.get("OK", False):
                resource_instance_remove_result = False
            instances_remove_results[instancename] = remove_result
        return {
            "OK": resource_instance_remove_result,
            'has_resource': True,
            'instances_remove_results': instances_remove_results
        }

    def resource_instance_remove(self, instancename):
        resource_instance = App.get_or_none(instancename)
        remove_result = resource_instance.basic_app_remove()
        if remove_result.get("OK", False):
            resource_instance.clear()
        return remove_result

    def basic_app_remove(self):
        logger.info("remove basic app : %s " % self.appname)
        remove_results = {}
        remove_success_results = {}
        remove_failed_results = {}
        remove_missed_results = {}
        try:
            app_spec = self.app_spec
            for pg_spec in app_spec.PodGroups:
                remove_r = self.podgroup_remove(pg_spec.Name)
                if remove_r.status_code < 400:
                    remove_success_results[pg_spec.Name] = remove_r
                elif remove_r.status_code == 404:
                    remove_missed_results[pg_spec.Name] = remove_r
                else:
                    remove_failed_results[pg_spec.Name] = remove_r
            # use dependency_remove api of Deployd for deleting proc with
            # portal type
            for dp_spec in app_spec.Portals:
                remove_r = self.dependency_remove(dp_spec.Name)
                if remove_r.status_code < 400:
                    remove_success_results[dp_spec.Name] = remove_r
                elif remove_r.status_code == 404:
                    remove_missed_results[dp_spec.Name] = remove_r
                else:
                    remove_failed_results[dp_spec.Name] = remove_r
        except Exception, e:
            logger.warning("failed when trying to remove app %s: %s" %
                           (self.appname, str(e)))
        remove_results = {
            'OK': len(remove_failed_results) == 0,
            'remove_success_results': remove_success_results,
            'remove_failed_results': remove_failed_results,
            'remove_missed_results': remove_missed_results
        }
        return remove_results

    @classmethod
    def get_portal_name_from_service_name(cls, service, service_name):
        if not service or not service.lain_config or not service.is_reachable():
            return 'portal-' + service_name
        for name, proc in service.lain_config.procs.iteritems():
            if proc.service_name == service_name:
                return name
        return None

    def get_service_name_from_portal_name(self, portal_name):
        portal_proc = self.lain_config.procs.get(portal_name, None)
        if portal_proc and portal_proc.service_name:
            return portal_proc.service_name
        return None

    def _fetch_ports_from_annotation(self, annotation_str):
        annotation = json.loads(annotation_str)
        ports = annotation.get('ports', None)
        if ports is not None:
            return [port['srcport'] for port in ports]
        return []

    def podgroup_deploy(self, podgroup_spec, autopatch=True):
        # do not consider the Dependency of the not-portal-type proc
        logger.info("deploy podgroup %s of app %s " %
                    (podgroup_spec.Name, self.appname))
        now_status = self.podgroup_status(podgroup_spec.Name)

        try:
            pod_ports = self._fetch_ports_from_annotation(
                podgroup_spec.Pod.Annotation)
            now_ports = self._fetch_ports_from_annotation(
                now_status['Status']['Spec']['Pod']['Annotation'])
            diff_ports = list(set(pod_ports) - set(now_ports))
            if len(diff_ports) > 0:
                diff_ports = {"Ports": diff_ports}
                resp = self.default_deploy.post_valiad_ports(diff_ports)
                if resp.status_code > 300:
                    return resp
        except Exception as e:
            logger.warning('validate ports error: %s' % e)

        for c in podgroup_spec.Pod.Containers:
            c.set_env('LAIN_APPNAME', podgroup_spec.Namespace)
            c.set_env('LAIN_APP_RELEASE_VERSION', self.meta_version)
            c.set_env('LAIN_PROCNAME', podgroup_spec.Name.split(".")[-1])
            c.set_env('LAIN_DOMAIN', MAIN_DOMAIN)
        if now_status is None:
            return self.default_deploy.create_podgroup(json_of_spec(podgroup_spec))
        else:
            if autopatch:
                # PATCH the origin cpu and memory to the new spec
                cpu = int(now_status['Status']['Spec'][
                          'Pod']['Containers'][0]['CpuLimit'])
                memory = int(now_status['Status']['Spec']['Pod'][
                             'Containers'][0]['MemoryLimit'])
                for c in podgroup_spec.Pod.Containers:
                    c.CpuLimit = cpu
                    c.MemoryLimit = memory
            return self.default_deploy.patch_podgroup_spec(json_of_spec(podgroup_spec))

    def podgroup_scale(self, podgroup_spec):
        logger.info("scale podgroup %s of app %s " %
                    (podgroup_spec.Name, self.appname))
        now_status = self.podgroup_status(podgroup_spec.Name)
        for c in podgroup_spec.Pod.Containers:
            c.set_env('LAIN_APPNAME', podgroup_spec.Namespace)
            c.set_env('LAIN_APP_RELEASE_VERSION', self.meta_version)
            c.set_env('LAIN_PROCNAME', podgroup_spec.Name.split(".")[-1])
            c.set_env('LAIN_DOMAIN', MAIN_DOMAIN)
        if now_status is None:
            return self.default_deploy.create_podgroup(json_of_spec(podgroup_spec))
        else:
            return self.default_deploy.patch_podgroup_instance(podgroup_spec.Name, podgroup_spec.NumInstances)

    def podgroup_remove(self, podgroup_name):
        logger.info("remove podgroup %s of app %s " %
                    (podgroup_name, self.appname))
        return self.default_deploy.remove_podgroup(podgroup_name)

    def dependency_register(self, service_app, service_appname, dependency_pod_name):
        # service may not been deployed yet, so may need force generate the
        # calico profile of service_profile
        service_app_profile = service_appname
        add_calico_profile_for_app(service_app_profile)

        client_app_profile = self.calico_profile
        portal_profile = "%s_%s" % (dependency_pod_name, self.appname)
        if add_calico_profile_for_app(portal_profile):
            calicoctl_profile_rule_op(
                portal_profile, "add inbound allow from tag %s --at=1" % client_app_profile)
            calicoctl_profile_rule_op(
                service_app_profile, "add inbound allow from tag %s --at=1" % portal_profile)

    def dependency_remove(self, dependency_pod_name):
        return self.default_deploy.remove_dependency(dependency_pod_name)

    def __unicode__(self):
        return '<%s:%s>' % (self.appname, self.meta_version)


def recursive_deploy(podgroup_spec):
    results = {}
    services_need_deploy = []
    services_dont_allow = []

    app = App.get(podgroup_spec.Namespace)
    services = app.lain_config.use_services
    for service_appname, service_procnames in services.iteritems():
        service_app = App.get_or_none(service_appname)
        if service_app is None or not service_app.is_reachable():
            logger.warning("service App %s DoesNotExist" % service_appname)
            services_need_deploy.extend(
                ["%s.proc.%s" % (service_appname, s) for s in service_procnames])
        for procname in service_procnames:  # TODO supporting service name alias
            portal_name = App.get_portal_name_from_service_name(
                service_app, procname)
            portal_pod_name = "%s.portal.%s" % (service_appname, portal_name)
            # TODO check portal.allow(client procname)
            app.dependency_register(
                service_app, service_appname, portal_pod_name)

    resources = app.lain_config.use_resources
    for resourcename, resource_props in resources.iteritems():
        instance_app = App.get_or_none(
            resource_instance_name(resourcename, app.appname))
        # TODO supporting resource name alias
        for procname in resource_props['services']:
            portal_name = App.get_portal_name_from_service_name(
                instance_app, procname)
            portal_pod_name = "%s.portal.%s" % (
                instance_app.appname, portal_name)
            # TODO check portal.allow(client procname)
            app.dependency_register(
                instance_app, instance_app.appname, portal_pod_name)

    results = {
        'services_need_deploy': services_need_deploy,
        'services_dont_allow': services_dont_allow,
    }

    podgroup_r = app.podgroup_deploy(podgroup_spec)
    results["podgroup_result"] = {
        podgroup_spec.Name: podgroup_r
    }
    results["OK"] = podgroup_r.status_code < 400
    return results


class Resource():

    instancename_prefix = 'resource'
    instancename_connector = '.'

    @classmethod
    def get_instance_image(cls, resourcename, meta_version):
        return "{}/{}:release-{}".format(PRIVATE_REGISTRY, resourcename, meta_version)

    @classmethod
    def get_resourcename_from_instancename(cls, instancename):
        return instancename.split('.')[1]

    @classmethod
    def get_clientappname_from_instancename(cls, instancename):
        return instancename.split('.')[2]

    @classmethod
    def get_instances(cls, resourcename):
        apps = App.all()
        resource_instances = []
        prefix = "%s%s%s%s" % (
            cls.instancename_prefix, cls.instancename_connector, resourcename, cls.instancename_connector)
        for app in apps:
            if app.appname.startswith(prefix) and app.is_reachable():
                resource_instances.append(app)
        return resource_instances


class Streamrouter():

    @classmethod
    def default_deploy(cls):
        return default_deploy

    @classmethod
    def get_streamrouter_ports(cls):
        r = cls.default_deploy().get_streamrouter_ports()
        if r.status_code < 400:
            return r.json()
        else:
            logger.error("fail to get ports of streamrouter")
            return None
