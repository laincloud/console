# -*- coding: utf-8

import re
import copy
import humanfriendly
import json
import jsonpickle
from lain_sdk.yaml.parser import ProcType, resource_instance_name
from .utils import get_system_volumes_from_etcd


class AppType:

    Normal = 'app'
    Service = 'service'
    Resource = 'resource'
    ResourceInstance = 'resource-instance'


class RestartPolicy:

    Never = 0
    Always = 1
    OnFail = 2


class DependencyPolicy:

    NamespaceLevel = 0
    NodeLevel = 1


class Dependency:

    PodName = ''
    Policy = DependencyPolicy.NamespaceLevel

    def clone(self):
        d = Dependency()
        d.PodName = self.PodName
        d.Policy = self.Policy
        return d

    def equals(self, d):
        return \
            d.PodName == self.PodName and \
            d.Policy == self.Policy


class ImSpec:

    Name = ''
    Namespace = ''
    Version = 0
    CreateAt = None
    UpdateAt = None


class CloudVolumeSpec:

    Type = ''
    Dirs = []

    def clone(self):
        cv = CloudVolumeSpec()
        cv.Type = self.Type
        cv.Dirs = self.Dirs
        return cv

    def verify_params(self):
        return \
            isinstance(self.Type, str) and \
            isinstance(self.Dirs, list)

    def equals(self, cv):
        if not isinstance(cv, CloudVolumeSpec):
            return False
        return \
            cv.Type == self.Type and \
            cv.Dirs == self.Dirs


class LogConfigSpec:

    Type = ''
    Config = {}

    def clone(self):
        lc = None
        return lc

    def verify_params(self):
        return \
            isinstance(self.Type, str) and \
            isinstance(self.Config, dict)

    def equals(self, s):
        if not isinstance(s, LogConfigSpec):
            return False
        return \
            s.Type == self.Type and \
            s.Config == self.Config


class ContainerSpec(ImSpec):

    Image = ''
    Env = []
    User = ''
    WorkingDir = ''
    DnsSearch = []
    Volumes = []
    SystemVolumes = []
    CloudVolumes = []
    Command = []
    Entrypoint = []
    CpuLimit = 0
    MemoryLimit = 0
    Expose = 0
    LogConfig = None

    def clone(self):
        s = ContainerSpec()
        s.Name = self.Name
        s.Namespace = self.Namespace
        s.Version = self.Version
        s.CreateAt = self.CreateAt
        s.UpdateAt = self.UpdateAt
        s.Image = self.Image
        s.Env = copy.deepcopy(self.Env)
        s.User = self.User
        s.WorkingDir = self.WorkingDir
        s.DnsSearch = copy.deepcopy(self.DnsSearch)
        s.Volumes = copy.deepcopy(self.Volumes)
        s.SystemVolumes = copy.deepcopy(self.SystemVolumes)
        s.CloudVolumes = copy.deepcopy(self.CloudVolumes)
        s.Command = copy.deepcopy(self.Command)
        s.Entrypoint = copy.deepcopy(self.Entrypoint)
        s.CpuLimit = self.CpuLimit
        s.MemoryLimit = self.MemoryLimit
        s.Expose = self.Expose
        if isinstance(self.LogConfig, LogConfigSpec):
            s.LogConfig = self.LogConfig.clone()
        return s

    def verify_params(self):
        logconfig_flag = True if self.LogConfig is None else self.LogConfig.verify_params()
        return \
            self.Image != "" and \
            self.CpuLimit >= 0 and \
            self.MemoryLimit >= 0 and \
            self.Expose >= 0 and \
            logconfig_flag

    def equals(self, s):
        if not isinstance(s, ContainerSpec):
            return False
        if self.LogConfig is None and s.LogConfig is None:
            logconfig_flag = True
        else:
            logconfig_flag = s.LogConfig.equals(self.LogConfig)
        return \
            s.Name == self.Name and \
            s.Namespace == self.Namespace and \
            s.CreateAt == self.CreateAt and \
            s.UpdateAt == self.UpdateAt and \
            s.Image == self.Image and \
            s.Env == self.Env and \
            s.User == self.User and \
            s.WorkingDir == self.WorkingDir and \
            s.DnsSearch == self.DnsSearch and \
            s.Volumes == self.Volumes and \
            s.SystemVolumes == self.SystemVolumes and \
            s.CloudVolumes == self.CloudVolumes and \
            s.Command == self.Command and \
            s.Entrypoint == self.Entrypoint and \
            s.CpuLimit == self.CpuLimit and \
            s.MemoryLimit == self.MemoryLimit and \
            s.Expose == self.Expose and \
            logconfig_flag

    def set_env(self, env_key, env_value):
        for i in self.Env:
            if re.match("%s\s*=" % env_key, i):
                self.Env.remove(i)
        self.Env.append("%s=%s" % (env_key, env_value))


class PodSpec(ImSpec):

    Containers = []
    Filters = []
    Labels = {}
    Dependencies = []
    Annotation = ''
    Stateful = False
    SetupTime = 0
    KillTimeout = 10
    HealthConfig = {}

    def clone(self):
        s = PodSpec()
        s.Name = self.Name
        s.Namespace = self.Namespace
        s.Version = self.Version
        s.CreateAt = self.CreateAt
        s.UpdateAt = self.UpdateAt
        s.Containers = [c.clone() for c in self.Containers]
        s.Labels = copy.deepcopy(self.Labels)
        s.Filters = copy.deepcopy(self.Filters)
        s.HealthConfig = copy.deepcopy(self.HealthConfig)
        s.Dependencies = [d.clone() for d in self.Dependencies]
        s.Annotation = self.Annotation
        s.Stateful = self.Stateful
        s.SetupTime = self.SetupTime
        s.KillTimeout = self.KillTimeout
        return s

    def verify_params(self):
        verify = \
            self.Name != "" and \
            self.Namespace != "" and \
            isinstance(self.Stateful, bool) and \
            len(self.Containers) > 0
        if not verify:
            return False
        for c in self.Containers:
            if isinstance(c, ContainerSpec) and c.verify_params():
                continue
            else:
                return False
        return True

    def equals(self, s):
        if not isinstance(s, PodSpec):
            return False
        if len(s.Containers) != len(self.Containers):
            return False
        for i in range(0, len(s.Containers)):
            if not s.Containers[i].equals(self.Containers[i]):
                return False
        if len(s.Dependencies) != len(self.Dependencies):
            return False
        for i in range(0, len(s.Dependencies)):
            if not s.Dependencies[i].equals(self.Dependencies[i]):
                return False
        return \
            s.Name == self.Name and \
            s.Namespace == self.Namespace and \
            s.Annotation == self.Annotation and \
            s.Stateful == self.Stateful and \
            s.Filters == self.Filters and \
            s.SetupTime == self.SetupTime and \
            s.KillTimeout == self.KillTimeout and \
            s.Labels == self.Labels and \
            s.HealthConfig == self.HealthConfig


class PodGroupSpec(ImSpec):

    Pod = None
    NumInstances = 0
    RestartPolicy = RestartPolicy.Never

    def clone(self):
        s = PodGroupSpec()
        s.Name = self.Name
        s.Namespace = self.Namespace
        s.Pod = self.Pod.clone()
        s.NumInstances = self.NumInstances
        s.RestartPolicy = self.RestartPolicy
        return s

    def verify_params(self):
        return \
            self.Name != "" and \
            self.Namespace != "" and \
            self.NumInstances >= 0 and \
            isinstance(self.Pod, PodSpec) and \
            self.Pod.verify_params()

    def equals(self, s):
        return \
            s.Name == self.Name and \
            s.Namespace == self.Namespace and \
            s.NumInstances == self.NumInstances and \
            s.RestartPolicy == self.RestartPolicy and \
            s.Pod.equals(self.Pod)


class AppSpec:

    AppName = ''
    PodGroups = []

    def clone(self):
        s = AppSpec()
        s.AppName = self.AppName
        s.PodGroups = [pg.clone() for pg in self.PodGroups]
        return s

    def verify_params(self):
        verify = self.AppName != ""
        if not verify:
            return False
        for pg in self.PodGroups:
            if isinstance(pg, PodGroupSpec) and pg.verify_params():
                continue
            else:
                return False
        return True

    def equals(self, s):
        if not isinstance(s, AppSpec):
            return False
        if s.AppName != self.AppName:
            return False
        if len(s.PodGroups) != len(self.PodGroups):
            return False
        for i in range(0, len(s.PodGroups)):
            if not s.PodGroups[i].equals(self.PodGroups[i]):
                return False
        return True


def render_app_spec(lain_config):
    app = AppSpec()
    app.AppName = lain_config.appname
    app.PodGroups = [render_podgroup_spec(app.AppName, proc, lain_config.use_services, lain_config.use_resources)
                     for proc in lain_config.procs.values() if proc.type != ProcType.portal]
    app.Portals = [render_pod_spec(app.AppName, proc, lain_config.use_services, lain_config.use_resources)
                   for proc in lain_config.procs.values() if proc.type == ProcType.portal]
    return app


def render_podgroup_spec(app_name, proc, use_services, use_resources):
    pod_group = PodGroupSpec()
    pod_group.Name = "%s.%s.%s" % (
        app_name, proc.type.name, proc.name
    )
    pod_group.Namespace = app_name
    pod_group.NumInstances = proc.num_instances
    pod_group.RestartPolicy = RestartPolicy.Always  # TODO allow user definiton
    pod_group.Pod = render_pod_spec(
        app_name, proc, use_services, use_resources)
    return pod_group


def render_pod_spec(app_name, proc, use_services, use_resources):
    pod = PodSpec()
    pod.Name = "%s.%s.%s" % (
        app_name, proc.type.name, proc.name
    )
    pod.Namespace = app_name
    pod.Containers = [render_container_spec(app_name, proc)]
    pod.Dependencies = []
    for service_app, service_list in use_services.iteritems():
        for service in service_list:
            pod.Dependencies.append(render_dependency(service_app, service))
    if use_resources:
        for resource_name, resource_props in use_resources.iteritems():
            resource_service_names = resource_props['services']
            for resouce_service_proc_name in resource_service_names:
                pod.Dependencies.append(render_dependency(resource_instance_name(
                    resource_name, app_name), resouce_service_proc_name))
    pod.Annotation = proc.annotation
    pod.Stateful = proc.stateful
    pod.SetupTime = proc.setup_time
    pod.KillTimeout = proc.kill_timeout
    pod.Labels = {} if not proc.labels else proc.labels
    pod.Filters = [] if not proc.filters else proc.filters
    pod.HealthConfig = {} if not proc.container_healthcheck else proc.container_healthcheck
    return pod


def render_container_spec(app_name, proc):
    c = ContainerSpec()
    c.Image = proc.image
    c.Env = copy.deepcopy(proc.env)
    c.set_env("TZ", 'Asia/Shanghai')
    c.User = '' if not hasattr(proc, 'user') else proc.user
    c.WorkingDir = '' if not hasattr(proc, 'working_dir') else proc.working_dir
    c.DnsSearch = [] if not hasattr(
        proc, 'dns_search') else copy.deepcopy(proc.dns_search)
    c.Volumes = copy.deepcopy(proc.volumes)
    c.SystemVolumes = copy.deepcopy(
        proc.system_volumes) + get_system_volumes_from_etcd(app_name)
    c.CloudVolumes = render_cloud_volumes(proc.cloud_volumes)
    c.Command = proc.cmd
    c.Entrypoint = proc.entrypoint
    c.CpuLimit = proc.cpu
    c.MemoryLimit = humanfriendly.parse_size(proc.memory)
    c.Expose = 0 if not proc.port else proc.port.keys()[0]
    c.LogConfig = None
    return c


def render_dependency(service_app, service):
    from apis.models import App
    d = Dependency()
    d.PodName = "%s.portal.%s" % (
        service_app,
        App.get_portal_name_from_service_name(
            App.get_or_none(service_app), service)
    )
    d.Policy = DependencyPolicy.NamespaceLevel  # TODO allow user definiton
    return d


def render_cloud_volumes(cloud_volumes):
    volumes = []
    for vol_type, vol_dirs in cloud_volumes.iteritems():
        cv = CloudVolumeSpec()
        cv.Type = vol_type
        cv.Dirs = vol_dirs
        volumes.append(cv)
    return volumes


def json_of_spec(spec):
    return json.loads(jsonpickle.encode(spec, unpicklable=False))


def render_podgroup_spec_from_json(spec_json):
    pod_group = PodGroupSpec()
    pod_group.Name = spec_json['Name']
    pod_group.Namespace = spec_json['Namespace']
    pod_group.NumInstances = spec_json['NumInstances']
    pod_group.RestartPolicy = spec_json['RestartPolicy']
    pod_group.Pod = render_pod_spec_from_json(spec_json['Pod'])
    return pod_group


def render_pod_spec_from_json(spec_json):
    pod = PodSpec()
    pod.Name = spec_json['Name']
    pod.Namespace = spec_json['Namespace']
    containers = spec_json.get('Containers')
    if not isinstance(containers, list):
        containers = []
    pod.Containers = [render_container_spec_from_json(
        pod.Name, c) for c in containers]
    dependencies = spec_json.get('Dependencies')
    if not isinstance(dependencies, list):
        dependencies = []
    pod.Dependencies = [render_dependency_from_json(d) for d in dependencies]
    pod.Annotation = spec_json['Annotation']
    pod.Stateful = spec_json.get('Stateful', False)
    pod.SetupTime = spec_json.get('SetupTime', 0)
    pod.KillTimeout = spec_json.get('KillTimeout', 10)
    pod.Version = spec_json['Version']
    filters = spec_json.get('Filters')
    if not isinstance(filters, list):
        filters = []
    pod.Filters = copy.deepcopy(filters)
    return pod


def render_container_spec_from_json(app_name, spec_json):
    c = ContainerSpec()
    c.Image = spec_json['Image']
    c.Env = copy.deepcopy(spec_json['Env'])
    c.User = spec_json['User']
    c.WorkingDir = spec_json['WorkingDir']
    c.DnsSearch = copy.deepcopy(
        spec_json['DnsSearch']) if spec_json.get('DnsSearch') else []
    c.Volumes = copy.deepcopy(spec_json['Volumes'])
    c.SystemVolumes = copy.deepcopy(spec_json['SystemVolumes'])
    cloud_volumes = spec_json.get('CloudVolumes')
    if not isinstance(cloud_volumes, list):
        cloud_volumes = []
    c.CloudVolumes = [render_cloud_volumes_spec_from_json(
        cv) for cv in cloud_volumes]
    command = spec_json.get('Command')
    if not command:
        command = []
    c.Command = command
    entrypoint = spec_json.get('entrypoint')
    if not entrypoint:
        entrypoint = []
    c.Entrypoint = entrypoint
    c.CpuLimit = spec_json['CpuLimit']
    c.MemoryLimit = spec_json['MemoryLimit']
    c.Expose = spec_json['Expose'] if spec_json['Expose'] else 0
    json_logconfig = spec_json.get('LogConfig', {})
    c.LogConfig = LogConfigSpec()
    c.LogConfig.Type = json_logconfig.get('Type', '')
    c.LogConfig.Config = copy.deepcopy(
        json_logconfig['Config']) if json_logconfig.get('Config') else {}
    return c


def render_dependency_from_json(spec_json):
    d = Dependency()
    d.PodName = spec_json['PodName']
    d.Policy = spec_json['Policy']
    return d


def render_cloud_volumes_spec_from_json(spec_json):
    cv = CloudVolumeSpec()
    cv.Type = spec_json['Type']
    cv.Dirs = spec_json['Dirs']
    return cv
