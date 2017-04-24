# -*- coding: utf-8

import yaml
import json
import collections
from etcd import EtcdKeyNotFound
from .specs import render_app_spec, AppType
from lain_sdk.yaml.parser import ProcType, LainConf
from commons.settings import PRIVATE_REGISTRY
from .utils import (
    normalize_meta_version,
    search_images_from_registry,
    get_meta_from_registry,
    read_from_etcd,
    delete_from_etcd,
    set_value_to_etcd,
    get_meta_version_from_tag,
    get_current_time,
    get_domains,
)
from commons.miscs import (
    InvalidMetaVersion,
    InvalidLainYaml,
    InvalidStoreData,
    DoesNotExist,
)
from log import logger


APP_RUNNING_STATE = {
    'REPO': 'reposited',
    'DEPLOYING': 'deploying',
    'DEPLOY': 'deployed'
}


class BaseApp:

    ETCD_PREFIX = '/lain/fake'

    appname = ''
    meta_version = ''
    meta = ''
    default_image = ''
    running_state = ''
    app_type = ''
    last_error = ''
    last_update = ''

    # property saved in memory but not in etcd
    _registry_tags = []
    _latest_meta_version = ''
    _app_spec = None
    _lain_config = None

    @classmethod
    def etcd_app_key(cls, appname):
        assert appname
        return "%s/%s" % (cls.ETCD_PREFIX, appname)

    @classmethod
    def render_app_from_etcd_value(cls, etcd_value):
        try:
            app_info = json.loads(etcd_value)
            appname = app_info.get('appname', '')
            meta_version = app_info.get('meta_version', '')
            meta = app_info.get('meta', '')
            default_image = app_info.get('default_image', '')
            running_state = app_info.get('running_state', None)
            app_type = app_info.get('app_type', None)
            last_update = app_info.get('last_update', '')
            last_error = app_info.get('last_error', '')
            if appname == '':
                raise InvalidStoreData("appname should not be empty")
            app = cls()
            app.appname = appname
            app.meta_version = meta_version
            app.meta = meta
            app.default_image = default_image
            app.running_state = running_state
            app.app_type = app_type
            app.last_update = last_update
            app.last_error = last_error
            return app
        except ValueError, e:
            raise InvalidStoreData(e)

    @classmethod
    def get_or_none(cls, appname):
        app = None
        try:
            app = cls.get(appname)
        except DoesNotExist:
            pass
        return app

    @classmethod
    def get(cls, appname):
        try:
            etcd_r = read_from_etcd(cls.etcd_app_key(appname))
            if etcd_r.dir:
                raise InvalidStoreData("Store Data should not be dir")
        except EtcdKeyNotFound, e:
            raise DoesNotExist(e)
        return cls.render_app_from_etcd_value(etcd_r.value)  # pylint: disable=E1103

    @classmethod
    def all(cls):
        try:
            apps_root_r = read_from_etcd(cls.ETCD_PREFIX)
        except EtcdKeyNotFound, e:
            logger.warn("call App.all() fail: %s" % e)
            return []
        apps = []
        for l in apps_root_r.leaves:
            appname = l.key[len(cls.ETCD_PREFIX) + 1:]  # FIXME: ugly
            try:
                app = cls.get(appname)
                apps.append(app)
            except:
                logger.error("error getting app %s from etcd" % appname)
        return apps

    @classmethod
    def create(cls, appname):
        app = cls()
        app.appname = appname
        app.running_state = APP_RUNNING_STATE['REPO']
        app.save()
        return app

    def clear(self):
        self.meta_version = ''
        self.meta = ''
        self.app_type = ''
        self.last_error = ''
        self.running_state = APP_RUNNING_STATE['REPO']
        self.save()

    def delete(self):
        delete_from_etcd(self.etcd_key)

    def save(self):
        self.last_update = get_current_time()
        etcd_value = json.dumps({
            'appname': self.appname,
            'meta_version': self.meta_version,
            'meta': self.meta,
            'default_image': self.default_image,
            'running_state': self.running_state,
            'app_type': self.app_type,
            'last_update': self.last_update,
            'last_error': self.last_error,
        })
        set_value_to_etcd(self.etcd_key, etcd_value)

    @property
    def lain_config(self):
        if self._lain_config is None:
            self._lain_config = self._get_lain_config()
        return self._lain_config

    def _get_lain_config(self):
        if self.meta == '' or self.meta_version == '':
            return None
        config = LainConf()
        config.load(self.meta, self.meta_version, self.default_image,
                    registry=PRIVATE_REGISTRY, domains=get_domains())
        return config

    @property
    def app_spec(self):
        if self._app_spec is None:
            self._app_spec = render_app_spec(self.lain_config)
        return self._app_spec

    def podgroup_spec(self, name):
        for pg in self.app_spec.PodGroups:
            if pg.Name == name:
                return pg
        return None

    def portal_spec(self, name):
        for p in self.app_spec.Portals:
            if p.Name == name:
                return p
        return None

    @property
    def latest_meta_version(self):
        if len(self._latest_meta_version) == 0:
            versions = self.availabe_meta_versions()
            if len(versions) == 0:
                return None
            else:
                self._latest_meta_version = versions[0]
        return self._latest_meta_version

    def availabe_meta_versions(self):
        logger.debug("try to get available meta version of app %s" %
                     self.appname)
        tags = self.registry_tags
        versions = {}
        for k in tags:
            meta_version = get_meta_version_from_tag(k)
            if meta_version:
                _timestamp = float(meta_version.split('-')[0])
                versions[_timestamp] = meta_version
        ordered_versions = collections.OrderedDict(
            sorted(versions.items(), reverse=True))
        logger.debug(
            "finish getting available meta version of app %s" % self.appname)
        return ordered_versions.values()

    @property
    def registry_tags(self):
        if len(self._registry_tags) == 0:
            self._registry_tags = self.docker_image_tags()
        return self._registry_tags

    def docker_image_tags(self):
        images = search_images_from_registry(
            app=self._get_registry_search_name())
        return images.get('tags', [])

    def _get_registry_search_name(self):
        return self.appname if self.appname.find('.') < 0 else self.appname.split('.')[1]

    @property
    def etcd_key(self):
        return self.etcd_app_key(self.appname)

    def get_app_type(self):
        if not self.app_type:
            self.update_app_type()
        return self.app_type

    def update_app_type(self):
        self.app_type = self._load_apptype_from_meta()
        if self.appname.startswith('resource.'):
            self.app_type = AppType.ResourceInstance
        else:
            for proc in self.lain_config.procs.values():
                if proc.type == ProcType.portal and self.app_type == AppType.Normal:
                    self.app_type = AppType.Service
        self.save()

    def _load_apptype_from_meta(self):
        try:
            if self.meta == '' or self.meta_version == '':
                return 'unknown'
            y = yaml.safe_load(self.meta)
            return y.get('apptype', AppType.Normal)
        except:
            return 'unknown'

    def clear_last_error(self):
        if self.last_error != '':
            self.last_error = ''
            self.save()

    def update_last_error(self, err_msg):
        self.last_error = err_msg
        self.save()

    def is_reachable(self):
        return self.running_state != APP_RUNNING_STATE['REPO']

    def set_deploying(self):
        self.running_state = APP_RUNNING_STATE['DEPLOYING']
        self.save()

    def set_deployed(self):
        self.running_state = APP_RUNNING_STATE['DEPLOY']
        self.save()

    def fetch_meta(self, meta_version):
        return get_meta_from_registry(self.appname, meta_version)

    def base_update_meta(self, meta_version, force=False):
        try:
            meta_version = normalize_meta_version(meta_version)
        except Exception, e:
            raise InvalidMetaVersion(e)
        if meta_version == self.meta_version and not force:
            return 'meta_version is already latest'
        meta = self.fetch_meta(meta_version)
        if not isinstance(meta, dict):
            return None
        self.meta = yaml.safe_dump(meta, default_style='"')
        self.meta_version = meta_version
        if self.appname != meta['appname']:
            raise InvalidLainYaml("appname dont match: %s" % meta)
        self.save()
        return 'meta updated'

    def update_meta(self, meta_version, meta=None, force=False,
                    update_lain_config=True, update_spec=True):
        if meta is not None:
            logger.debug("meta of app `%s` was specified to `%s`" %
                         (self.appname, meta))
            self.meta = meta
            self.save()
            result = "meta specified"
        else:
            logger.debug("try to update meta of app `%s` to meta version `%s`" % (
                self.appname, meta_version))
            result = self.base_update_meta(meta_version, force)
        if update_lain_config:
            self.lain_config = self._get_lain_config()
        if update_spec:
            self.app_spec = render_app_spec(self.lain_config)
        logger.debug("finish updating meta of app `%s`" % self.appname)
        return result

    def check_latest_version(self):
        logger.debug("check latest version of app %s" % self.appname)
        latest_version = self.latest_meta_version
        if latest_version:
            release_version = "%s-%s" % ("release", latest_version)
            if release_version in self.registry_tags:
                return True, latest_version
        return False, None

    def __unicode__(self):
        return '<%s:%s>' % (self.appname, self.meta_version)
