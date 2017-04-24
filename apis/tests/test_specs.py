# -*- coding: utf-8

from apis.specs import (RestartPolicy, DependencyPolicy)
from apis.specs import (ImSpec, Dependency, LogConfigSpec, ContainerSpec,
                        PodSpec, PodGroupSpec, AppSpec)


def test_ImSpec_smoke():
    s = ImSpec()
    assert s.CreateAt is None
    assert s.Name == ""


def test_Dependency_smoke():
    d = Dependency()
    assert d.PodName == ""
    assert d.Policy == DependencyPolicy.NamespaceLevel


def test_Dependency_util_smoke():
    d1 = Dependency()
    d1.PodName = 'hello.foo.bar'
    d1.Policy = DependencyPolicy.NodeLevel
    d2 = d1.clone()
    assert d1 != d2
    assert d2.equals(d1)


def test_LogConfigSpec_smoke():
    l = LogConfigSpec()
    assert l.Type == ''
    assert l.Config == {}


def test_LogConfigSpec_verify_params_smoke():
    l = LogConfigSpec()
    l.Type = None
    assert not l.verify_params()
    l.Type = 'logd'
    l.Config = {}
    assert l.verify_params()


def test_ContainerSpec_smoke():
    s = ContainerSpec()
    assert s.Name == ""
    assert s.Namespace == ""
    assert s.CreateAt is None
    assert s.Version == 0
    assert s.Image == ""
    assert s.Command == []
    assert s.LogConfig is None


def test_ContainerSpec_verify_params_smoke():
    s = ContainerSpec()
    assert not s.verify_params()
    s.Image = 'hello/release-123-456'
    assert s.verify_params()
    s.LogConfig = LogConfigSpec()
    assert s.verify_params()


def test_ContainerSpec_util_smoke():
    s1 = ContainerSpec()
    s2 = s1.clone()
    assert s1 != s2
    assert s1.equals(s2)
    s1.LogConfig = LogConfigSpec()
    s2.LogConfig = LogConfigSpec()
    s1.LogConfig.Type = 'syslogd'
    assert not s1.equals(s2)


def test_PodSpec_smoke():
    s = PodSpec()
    s.Containers = [ContainerSpec()]
    s.Dependencies = [Dependency()]
    assert s.Name == ""
    assert s.Annotation == ""


def test_PodSpec_util_smoke():
    s1 = PodSpec()
    s1.Containers = [ContainerSpec()]
    s1.Dependencies = [Dependency()]
    s2 = s1.clone()
    assert s1 != s2
    assert s1.equals(s2)
    assert s1.Containers[0] != s2.Containers[0]
    assert s1.Containers[0].equals(s2.Containers[0])
    assert s1.Dependencies[0] != s2.Dependencies[0]
    assert s1.Dependencies[0].equals(s2.Dependencies[0])


def test_PodSpec_verify_params_smoke():
    c = ContainerSpec()
    d = Dependency()
    s = PodSpec()
    s.Containers = [c]
    s.Dependencies = [d]
    assert not s.verify_params()
    s.Name = "web"
    s.Namespace = "hello.foo.bar"
    assert not s.verify_params()
    c.Image = "hello/release-123-456"
    assert s.verify_params()


def test_PodGroupSpec_smoke():
    p = PodSpec()
    p.Containers = [ContainerSpec()]
    p.Dependencies = [Dependency()]
    s = PodGroupSpec()
    s.Pod = p
    assert s.NumInstances == 0
    assert s.RestartPolicy == RestartPolicy.Never


def test_PodGroupSpec_util_smoke():
    c = ContainerSpec()
    d = Dependency()
    p = PodSpec()
    p.Containers = [c]
    p.Dependencies = [d]
    s1 = PodGroupSpec()
    s1.Pod = p
    s1.NumInstances = 1
    s1.RestartPolicy = RestartPolicy.OnFail
    s2 = s1.clone()
    assert s1 != s2
    assert s1.equals(s2)
    p1 = s1.Pod
    p2 = s2.Pod
    assert p1 != p2
    assert p1.equals(p2)
    assert p1.Containers[0] != p2.Containers[0]
    assert p1.Containers[0].equals(p2.Containers[0])
    assert p1.Dependencies[0] != p2.Dependencies[0]
    assert p1.Dependencies[0].equals(p2.Dependencies[0])


def test_PodGroupSpec_verify_params_smoke():
    c = ContainerSpec()
    d = Dependency()
    p = PodSpec()
    p.Containers = [c]
    p.Dependencies = [d]
    s = PodGroupSpec()
    s.Pod = p
    s.NumInstances = 1
    s.RestartPolicy = RestartPolicy.OnFail
    assert not s.verify_params()
    s.Name = "web"
    s.Namespace = "hello.foo.bar"
    assert not s.verify_params()
    p.Name = "web"
    p.Namespace = "hello.foo.bar"
    assert not s.verify_params()
    c.Image = "hello/release-123-456"
    assert s.verify_params()


def test_AppSpec_smoke():
    p = PodSpec()
    p.Containers = [ContainerSpec()]
    p.Dependencies = [Dependency()]
    pg = PodGroupSpec()
    pg.Pod = p
    a = AppSpec()
    a.PodGroups = [pg]
    assert a.AppName == ""


def test_AppSpec_util_smoke():
    c = ContainerSpec()
    d = Dependency()
    p = PodSpec()
    p.Containers = [c]
    p.Dependencies = [d]
    pg = PodGroupSpec()
    pg.Pod = p
    pg.NumInstances = 1
    pg.RestartPolicy = RestartPolicy.OnFail
    a1 = AppSpec()
    a1.AppName = "hello"
    a1.PodGroups = [pg]
    a2 = a1.clone()
    assert a1 != a2
    assert a1.equals(a2)
    pg1 = a1.PodGroups[0]
    pg2 = a2.PodGroups[0]
    assert pg1 != pg2
    assert pg1.equals(pg2)


def test_AppSpec_verify_params_smoke():
    c = ContainerSpec()
    d = Dependency()
    p = PodSpec()
    p.Containers = [c]
    p.Dependencies = [d]
    pg = PodGroupSpec()
    pg.Pod = p
    pg.NumInstances = 1
    pg.RestartPolicy = RestartPolicy.OnFail
    a = AppSpec()
    a.PodGroups = [pg]
    assert not a.verify_params()
    a.AppName = "hello"
    assert not a.verify_params()
    pg.Name = "web"
    pg.Namespace = "hello.foo.bar"
    assert not a.verify_params()
    p.Name = "web"
    p.Namespace = "hello.foo.bar"
    assert not a.verify_params()
    c.Image = "hello/release-123-456"
    assert a.verify_params()
