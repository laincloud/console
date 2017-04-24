# -*- coding: utf-8

import copy
import humanfriendly
from threading import Thread
from .models import App, Resource, Streamrouter, recursive_deploy, default_deploy
from .specs import render_podgroup_spec_from_json, AppType
from authorize.models import Authorize, Group
from configs.models import Config
from commons.miscs import InvalidMetaVersion, NoAvailableImages
from commons.settings import PRIVATE_REGISTRY, AUTH_TYPES
from .utils import convert_time_from_deployd
from lain_sdk.yaml.parser import ProcType, resource_instance_name
from django.core.urlresolvers import reverse
from raven.contrib.django.raven_compat.models import client
from log import logger, op_logger


def render_op_result(op_result):
    try:
        return {
            "status_code": op_result.status_code,
            "data": op_result.json().get('message')
        }
    except Exception:
        return {
            "status_code": op_result.status_code,
            "data": op_result.content
        }


def render_op_result_to_msg(op_result):
    d = render_op_result(op_result)
    return "    status_code: %s\n" % (d['status_code']) + \
        "    message: %s" % (d['data'])


def render_podgroup_deploy_result_to_msg(deploy_result):
    msg = '    OK: %s\n' % deploy_result.get('OK', False)
    msg += '    podgroup_result:\n'
    for pgname, pgr in deploy_result['podgroup_result'].iteritems():
        msg += '    %s\n%s\n' % (pgname, render_op_result_to_msg(pgr))
    msg += '    services_need_deploy:\n'
    for pgname in deploy_result['services_need_deploy']:
        msg += '    %s\n' % (pgname)
    return msg


def render_basic_app_deploy_result_to_msg(deploy_result):
    if not deploy_result:
        return 'OK: False \n app deploy failed!'
    msg = 'OK: %s\n' % deploy_result.get('OK', False)

    msg += '--proc_deploy_results--\n'
    proc_results = deploy_result['proc_results']
    msg += '  OK: %s \n' % proc_results.get('OK', False)
    msg += '  proc_deploy_success:\n'
    for pgname, pg_result in proc_results['proc_deploy_success'].iteritems():
        msg += '    %s\n%s\n' % (pgname,
                                 render_podgroup_deploy_result_to_msg(pg_result))
    msg += '  proc_deploy_failed:\n'
    for pgname, pg_result in proc_results['proc_deploy_failed'].iteritems():
        msg += '    %s\n%s\n' % (pgname,
                                 render_podgroup_deploy_result_to_msg(pg_result))
    msg += '\n'

    msg += '--portal_depoy_results--\n'
    portal_results = deploy_result['portal_results']
    msg += '  OK: %s \n' % portal_results.get('OK', False)
    msg += '  portals_register_success:\n'
    for pgname, pg_result in portal_results['portals_register_success'].iteritems():
        msg += '    %s\n%s\n' % (pgname, render_op_result_to_msg(pg_result))
    msg += '  portals_register_failed:\n'
    for pgname, pg_result in portal_results['portals_register_failed'].iteritems():
        msg += '    %s\n%s\n' % (pgname, render_op_result_to_msg(pg_result))
    msg += '  portals_update_success:\n'
    for pgname, pg_result in portal_results['portals_update_success'].iteritems():
        msg += '    %s\n%s\n' % (pgname, render_op_result_to_msg(pg_result))
    msg += '  portals_update_failed:\n'
    for pgname, pg_result in portal_results['portals_update_failed'].iteritems():
        msg += '    %s\n%s\n' % (pgname, render_op_result_to_msg(pg_result))
    msg += '\n'

    useless_procs_remove_results = deploy_result.get(
        'useless_procs_remove_results')
    if useless_procs_remove_results:
        msg += '--useless_procs_remove_results--\n'
        msg += render_basic_app_remove_result_to_msg(
            useless_procs_remove_results)
    return msg


def render_resource_deploy_result_to_msg(deploy_result):
    msg = 'OK: %s\n' % deploy_result.get('OK', False)
    msg += '  resources_need_deploy:\n'
    for rename in deploy_result['resources_need_deploy']:
        msg += '    %s\n' % (rename)

    msg += '  resouce_instances_deploy_results:\n'
    instance_results = deploy_result['instances_deploy_results']
    for riname, ri_result in instance_results.iteritems():
        msg += '%s\n%s\n' % (riname,
                             render_basic_app_deploy_result_to_msg(ri_result))
    return msg


def render_app_deploy_result_to_msg(deploy_result):
    msg = 'OK: %s\n' % deploy_result.get('OK', False)
    has_resource = deploy_result['dp_resources_deploy_results']['has_resource']
    if has_resource:
        resource_results = deploy_result['dp_resources_deploy_results']
        msg += 'dp_resource_instance_deploy_results:\n'
        msg += '%s\n' % (render_resource_deploy_result_to_msg(resource_results))

    app_results = deploy_result['app_deploy_results']
    msg += 'app_deploy_results:\n'
    msg += '%s\n' % (render_basic_app_deploy_result_to_msg(app_results))
    return msg


def render_podgroup_remove_result_to_msg(deploy_result):
    return render_op_result_to_msg(deploy_result)


def render_basic_app_remove_result_to_msg(deploy_result):
    msg = 'OK: %s\n' % deploy_result.get('OK', False)
    msg += 'remove_success_results:\n'
    for pgname, pgr in deploy_result['remove_success_results'].iteritems():
        msg += '  %s\n%s\n' % (pgname, render_op_result_to_msg(pgr))
    msg += 'remove_missed_results:\n'
    for pgname, pgr in deploy_result['remove_missed_results'].iteritems():
        msg += '  %s\n%s\n' % (pgname, render_op_result_to_msg(pgr))
    msg += 'remove_failed_results:\n'
    for pgname, pgr in deploy_result['remove_failed_results'].iteritems():
        msg += '  %s\n%s\n' % (pgname, render_op_result_to_msg(pgr))
    return msg


def render_app_remove_result_to_msg(remove_result):
    msg = 'OK: %s\n' % remove_result.get('OK', False)
    msg += 'app_remove_results:\n'
    msg += render_basic_app_remove_result_to_msg(
        remove_result['app_remove_results'])

    instance_remove_results = remove_result['dp_resources_remove_results']
    if instance_remove_results.get('has_resource', False):
        msg += 'resource_instance_remove_results:\n'
        for riname, remove_result in instance_remove_results['instances_remove_results'].iteritems():
            msg += '  %s\n%s\n' % (riname,
                                   render_basic_app_remove_result_to_msg(remove_result))
    return msg


def render_app_update_result_to_msg(update_result, is_resource_instance=False):
    msg = 'OK: %s\n' % update_result.get('OK', False)
    if not is_resource_instance:
        msg += 'dp_resource_update_results:\n'
        resource_update_results = update_result['dp_resources_update_results']
        msg += '  resource_instance_deploy_results:\n'
        msg += '    %s\n' % (render_resource_deploy_result_to_msg(resource_update_results))
        msg += '  resource_instance_remove_results:\n'
        for riname, remove_result in resource_update_results['instances_remove_results'].iteritems():
            msg += '    %s\n%s\n' % (riname,
                                     render_basic_app_remove_result_to_msg(remove_result))
        app_results = update_result['app_update_results']
    msg += 'app_update_results:\n'
    msg += '%s\n' % (render_basic_app_deploy_result_to_msg(
        update_result if is_resource_instance else app_results))
    return msg


def is_deployable():
    return default_deploy.is_deployable()


'''
这个类响应 console.views 的 对 App 相关的所有调用
请求成功完成应返回 status_code, view_object, msg, url 的 turple
status_code / view_object / msg / url 是自己渲染的
console.views 将上面的 turple 封装成 JsonResponse
'''


class AppApi:

    @classmethod
    def render_app(cls, app, iteration=True, client=None, use_portals=[]):
        appname, app_lain_conf, app_type = app.appname, app.lain_config, app.app_type
        last_error, last_update, app_status = app.last_error, app.last_update, app.app_status
        data = {
            'appname': appname,
            'apptype': app_type,
            'metaversion': '',
            'updatetime': last_update,
            'deployerror': last_error,
            'procs': [],
            'portals': [],
            'useservices': [],
            'useresources': [],
            'url': reverse('api_app', kwargs={'appname': appname})
        }
        if app_lain_conf is None:
            return data
        data['metaversion'] = app_lain_conf.meta_version

        if iteration:
            if len(app_lain_conf.use_services) > 0:
                useservices = []
                for service_appname, service_procname_list in app_lain_conf.use_services.iteritems():
                    service = App.get_or_none(service_appname)
                    use_portal_list = [App.get_portal_name_from_service_name(
                        service, s) for s in service_procname_list]
                    useservices.append({
                        'servicename': service_appname,
                        'serviceprocs': use_portal_list,
                        'service': {} if not service or not service.is_reachable() else
                        AppApi.render_app(
                            service, iteration=False, client=app_lain_conf.appname, use_portals=use_portal_list)
                    })
                data['useservices'] = useservices
            if len(app_lain_conf.use_resources) > 0:
                useresources = []
                for resource_appname, resource_info in app_lain_conf.use_resources.iteritems():
                    instance = App.get_or_none(resource_instance_name(
                        resource_appname, app_lain_conf.appname))
                    use_portal_list = [App.get_portal_name_from_service_name(
                        instance, s) for s in resource_info['services']]
                    useresources.append({
                        'resourcename': resource_appname,
                        'resourceprocs': use_portal_list,
                        'resourceinstance': {} if not instance or not instance.is_reachable() else
                        AppApi.render_app(
                            instance, iteration=False, client=app_lain_conf.appname, use_portals=use_portal_list)
                    })
                data['useresources'] = useresources

        procs, portals = [], []
        if app_status:
            data['deployerror'] = last_error if last_error else app_status[
                'LastError']
            for pg_status in app_status['PodGroups']:
                pg_name = pg_status['Name']
                procname = pg_name.split('.')[-1]
                proc_lain_conf = app_lain_conf.procs.get(procname, None)
                if proc_lain_conf:
                    procs.append(ProcApi.render_proc_data(
                        app_lain_conf.appname, proc_lain_conf, pg_status))
            for ps_status in app_status['Portals']:
                ps_name = ps_status['Name']
                portalname = ps_name.split('.')[-1]
                portal_lain_conf = app_lain_conf.procs.get(portalname, None)
                if portal_lain_conf:
                    if not iteration:
                        if portalname in use_portals:
                            portals.append(ProcApi.render_proc_data(
                                app_lain_conf.appname, portal_lain_conf, ps_status, is_portal=True, client=client))
                    else:
                        portals.append(ProcApi.render_proc_data(
                            app_lain_conf.appname, portal_lain_conf, ps_status, is_portal=True))
        else:
            # resource apps donot have app status
            for proc in app_lain_conf.procs.values():
                if proc.type == ProcType.portal:
                    portals.append(ProcApi.render_proc_data(
                        app_lain_conf.appname, proc))
                else:
                    procs.append(ProcApi.render_proc_data(
                        app_lain_conf.appname, proc))

        data['procs'] = procs
        data['portals'] = portals

        if app_type == AppType.Resource:
            instances = []
            for instance in Resource.get_instances(app_lain_conf.appname):
                instances.append(AppApi.render_app(instance))
            data['resourceinstances'] = instances
        return data

    @classmethod
    def render_repo_data(cls, appname):
        data = {
            'appname': appname,
            'url': reverse('api_repo', kwargs={'appname': appname}),
        }
        return data

    @classmethod
    def render_version_data(cls, appname, versions):
        data = {
            'appname': appname,
            'tags': versions,
            'url': reverse('api_versions', kwargs={'appname': appname}),
        }
        return data

    @classmethod
    def check_app_exist(cls, appname):
        app = App.get_or_none(appname)
        if not app:
            return False
        return True

    @classmethod
    def list_apps(cls, open_auth, groups, options=None):
        def verify_options(options):
            apptype, msg = '', ''
            if options:
                apptype = options.get('apptype', AppType.Normal)
            return True, msg, apptype
        is_valid, msg, apptype = verify_options(options)
        if not is_valid:
            return (400, None, msg, reverse('api_docs'))
        try:
            apps = App.all()
            if open_auth:
                app_datas = [AppApi.render_app(a) for a in apps if a.is_reachable()
                             and (True if apptype == '' else a.get_app_type() == apptype) and AuthApi.verify_app_access(groups, a.appname)]
            else:
                app_datas = [AppApi.render_app(a) for a in apps if a.is_reachable()
                             and (True if apptype == '' else a.get_app_type() == apptype)]
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when getting apps:\n%s\nplease contact with admin of lain\n' % e,
                    reverse('api_docs'))
        return (200, app_datas, '', reverse('api_apps'))

    @classmethod
    def list_repos(cls, open_auth, groups, options=None):
        try:
            apps = App.all()
            if open_auth:
                app_datas = [AppApi.render_repo_data(
                    a.appname) for a in apps if AuthApi.verify_app_access(groups, a.appname)]
            else:
                app_datas = [AppApi.render_repo_data(a.appname) for a in apps]
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when getting repos apps:\n%s\nplease contact with admin of lain\n' % e,
                    reverse('api_docs'))
        return (200, app_datas, '', reverse('api_repos'))

    @classmethod
    def create_app(cls, access_token, appname, options=None):
        try:
            app = App.get_or_none(appname)
            if app.is_reachable():
                return (409, AppApi.render_app(app),
                        'app with appname %s already exists\n' % appname,
                        reverse('api_app', kwargs={'appname': appname}))

            exist, target_meta_version = app.check_latest_version()
            if not exist:
                logger.error(
                    "app %s found no latest meta and release images" % appname)
                return (400, None,
                        'not found both meta and release images,\nplease check your App images then try to update your App\n',
                        reverse('api_app', kwargs={'appname': appname}))

            app.clear_last_error()
            app.set_deploying()
            t = Thread(target=cls._app_deploy_thread, args=(
                access_token, app, target_meta_version,))
            t.start()

            return (202, AppApi.render_app(app), 'deploy request of app %s has been accepted.' % appname,
                    reverse('api_app', kwargs={'appname': appname}))
        except InvalidMetaVersion, ime:
            return (500, None,
                    'error in parsing meta_version: %s\nplease check your App images then try to update your App\n' % ime,
                    reverse('api_app', kwargs={'appname': appname}))
        except NoAvailableImages, naie:
            return (500, None,
                    'error in getting images: %s\nplease check your App images then try to update your App\n' % naie,
                    reverse('api_app', kwargs={'appname': appname}))
        except Exception, e:
            return (500, None,
                    'fatal error when creating app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))

    @classmethod
    def _app_deploy_thread(cls, token, app, meta_version):
        try:
            op_logger.info("DEPLOY: app %s deployed by %s to version %s" % (
                app.appname, AuthApi.operater, meta_version))

            logger.info("ready create app %s" % app.appname)
            if not app.update_meta(meta_version, force=True, update_spec=False):
                raise Exception(
                    "error getting meta_version/meta %s for app %s" % (meta_version, app.appname))

            logger.info("update metaversion to %s" % meta_version)
            if app.get_app_type() != AppType.Resource:
                app.add_calico_profile()
                success, msg = AuthApi.create_resource_instance_group(
                    token, app.appname)
                if not success:
                    raise Exception(
                        "error creating resource instance group for app %s : %s" % (app.appname, msg))

                configed_instances = cls._get_configed_instances(
                    token, app, app.lain_config.use_resources)

                ConfigApi.construct_config_for_app(token, app)
                deploy_result = app.app_deploy(configed_instances)
                logger.info("%s deploy result: %s" % (
                    app.appname, render_app_deploy_result_to_msg(deploy_result)))
                if not deploy_result.get("OK", False):
                    raise Exception("error deploying : %s" %
                                    render_app_deploy_result_to_msg(deploy_result))
        except Exception, e:
            client.captureException()
            error_msg = "error deploying app %s : %s" % (app.appname, str(e))
            logger.error(error_msg)
            app.update_last_error(error_msg)
        finally:
            app.set_deployed()

    @classmethod
    def _get_configed_instances(cls, token, app, resources):
        configed_instances = {}
        if resources is None:
            return configed_instances

        for resourcename, resource_props in resources.iteritems():
            resource = App.get_or_none(resourcename)
            if resource is None or not resource.is_reachable():
                # resource not existed
                raise Exception(
                    "Error: Resource %s DoesNotExist" % resourcename)

            instancename = resource_instance_name(resourcename, app.appname)
            resource_instance = App.get_or_none(instancename)
            if not resource_instance:
                resource_instance = App.create(instancename)
            resource_instance.meta_version = resource.meta_version
            resource_instance.default_image = Resource.get_instance_image(
                resource.appname, resource.meta_version)
            resource_instance.meta = resource.get_resource_instance_meta(
                app.appname, resource_props['context'])
            resource_instance.add_calico_profile()

            ConfigApi.construct_config_for_instance(
                token, resource, resource_instance)
            configed_instances[instancename] = resource_instance
        return configed_instances

    @classmethod
    def create_repo(cls, access_token, appname, options=None):
        try:
            app = App.get_or_none(appname)
            if app:
                return (409, None, 'app with appname %s has already been reposited\n' % appname,
                        reverse('api_repo', kwargs={'appname': appname}))

            op_logger.info("REPOSIT: app %s reposited by %s" %
                           (appname, AuthApi.operater))

            app = App.create(appname)
            success, msg = Group.create_group_for_app(access_token, appname)
            if not success:
                app.delete()
                return (500, None, 'error reposing app %s : \n%s\n' % (appname, msg), reverse('api_docs'))
            else:
                return (201, AppApi.render_repo_data(appname), msg,
                        reverse('api_repo', kwargs={'appname': appname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when reposing app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))

    @classmethod
    def delete_app(cls, appname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))

            if app.get_app_type() == AppType.Resource:
                return (403, AppApi.render_app(app),
                        'Not allow to delete resource app.',
                        reverse('api_apps'))

            op_logger.info("DELETE: app %s deleted by %s" %
                           (appname, AuthApi.operater))
            logger.info("ready delete app %s" % appname)

            is_meta_empty = True
            if app.meta != '':
                is_meta_empty = False
                remove_results = app.app_remove()
                logger.info(render_app_remove_result_to_msg(remove_results))
                if not remove_results.get("OK", False):
                    return (500, None,
                            render_app_remove_result_to_msg(remove_results),
                            reverse('api_app', kwargs={'appname': appname}))
            app.clear()
            return (202, AppApi.render_repo_data(appname),
                    'delete app successfully.' if is_meta_empty else render_app_remove_result_to_msg(
                        remove_results),
                    reverse('api_apps'))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when delete app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_app', kwargs={'appname': appname}))

    @classmethod
    def update_app(cls, access_token, appname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))

            target_meta_version = options.get(
                'meta_version', None) if isinstance(options, dict) else None
            if target_meta_version and target_meta_version not in app.availabe_meta_versions():
                return (400, AppApi.render_app(app),
                        'no such meta_version %s for app %s\nplease check your images\n' % (
                            target_meta_version, appname),
                        reverse('api_app', kwargs={'appname': appname}))

            if appname.find('.') < 0 and target_meta_version is None:
                exist, target_meta_version = app.check_latest_version()
                if not exist:
                    return (400, None,
                            'can not get meta_version/meta\nplease check your App images then try to update your App\n',
                            reverse('api_app', kwargs={'appname': appname}))

            app.clear_last_error()
            app.set_deploying()
            t = Thread(target=cls._app_update_thread, args=(
                access_token, app, target_meta_version,))
            t.start()
            return (202, AppApi.render_app(app), 'update request of app %s has been accepted.' % appname,
                    reverse('api_app', kwargs={'appname': appname}))
        except InvalidMetaVersion, ime:
            return (500, None,
                    'error in parsing meta_version: %s\nplease check your App images then try to update your App\n' % ime,
                    reverse('api_app', kwargs={'appname': appname}))
        except Exception, e:
            return (500, None,
                    'fatal error when update app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_app', kwargs={'appname': appname}))

    @classmethod
    def _app_update_thread(cls, token, app, target_meta_version):
        former_version, former_meta = app.meta_version, app.meta
        try:
            if app.appname.find('.') > 0:
                cls._update_resource_instance(token, app, target_meta_version)
            else:
                cls._update_normal_app(token, app, target_meta_version)
        except Exception, e:
            client.captureException()
            error_msg = "error when updating app %s : %s" % (
                app.appname, str(e))
            logger.error(error_msg)
            # role back to the former version if error happends
            app.meta_version = former_version
            app.meta = former_meta
            app.update_last_error(error_msg)
        finally:
            app.set_deployed()

    @classmethod
    def _update_resource_instance(cls, token, instance, target_meta_version):
        op_logger.info("UPDATE: resource instance %s updated by %s to version %s" % (
            instance.appname, AuthApi.operater, target_meta_version))
        logger.info("ready update resource instance %s" % instance.appname)

        origin_procs = instance.lain_config.procs.values()

        # when updating resource instance, its target_meta_version should be
        # the latest meta_version of resource
        resourcename = Resource.get_resourcename_from_instancename(
            instance.appname)
        resource = App.get(resourcename)
        instance.meta_version = target_meta_version if target_meta_version else resource.meta_version
        instance.default_image = Resource.get_instance_image(
            resourcename, instance.meta_version)

        clientname = Resource.get_clientappname_from_instancename(
            instance.appname)
        client_app = App.get(clientname)
        resources = client_app.lain_config.use_resources

        for resource_appname, resource_props in resources.iteritems():
            if resource_appname == resourcename:
                updated_meta = resource.get_resource_instance_meta(
                    clientname, resource_props['context'])
                instance.update_meta(None, meta=updated_meta, update_spec=True)

        ConfigApi.construct_config_for_instance(token, resource, instance)
        update_result = instance.basic_app_deploy(origin_procs)
        logger.info("%s update result: %s" % (instance.appname,
                                              render_app_update_result_to_msg(update_result, is_resource_instance=True)))
        if not update_result.get("OK", False):
            raise Exception("error updating : %s" % render_app_update_result_to_msg(
                update_result, is_resource_instance=True))

    @classmethod
    def _update_normal_app(cls, token, app, target_meta_version):
        op_logger.info("UPDATE: app %s updated by %s to version %s" % (
            app.appname, AuthApi.operater, target_meta_version))

        # bachup the former setting
        origin_app = copy.deepcopy(app)
        origin_resource = {} if (
            app.lain_config is None) else app.lain_config.use_resources
        origin_procs = {} if (
            app.lain_config is None) else app.lain_config.procs.values()

        logger.info("ready update app %s" % app.appname)
        if not app.update_meta(target_meta_version, force=True,
                               update_spec=(app.get_app_type() != AppType.Resource)):
            logger.error('error when loading meta_version %s for app %s' %
                         (target_meta_version, app.appname))
            raise Exception('error when loading meta_version %s for app %s' % (
                target_meta_version, app.appname))

        logger.info("update metaversion to %s" % target_meta_version)
        if app.get_app_type() != AppType.Resource:
            success, msg = AuthApi.create_resource_instance_group(
                token, app.appname)
            if not success:
                AppApi.recover_fail_update(origin_app, app)
                logger.error('error when creating resource instance group for app %s : %s ' % (
                    app.appname, msg))
                raise Exception(
                    'error when creating resource instance group for app %s : %s ' % (app.appname, msg))

            configed_instances = cls._get_configed_instances(
                token, app, app.lain_config.use_resources)
            ConfigApi.construct_config_for_app(token, app)
            update_result = app.app_update(
                origin_resource, origin_procs, configed_instances)
            logger.info("%s update result: %s" % (
                app.appname, render_app_update_result_to_msg(update_result)))
            if not update_result.get("OK", False):
                raise Exception("error updating : %s" %
                                render_app_update_result_to_msg(update_result))

    @classmethod
    def recover_fail_update(self, origin_app, new_app):
        new_app.meta = origin_app.meta
        new_app.meta_version = origin_app.meta_version
        new_app.save()

    @classmethod
    def get_app(cls, appname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))
            return (200, AppApi.render_app(app),
                    '', reverse('api_app', kwargs={'appname': appname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when get app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_app', kwargs={'appname': appname}))

    @classmethod
    def get_repo(cls, appname, options=None):
        try:
            return (200, AppApi.render_repo_data(appname),
                    '', reverse('api_repo', kwargs={'appname': appname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when get repo app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_repo', kwargs={'appname': appname}))

    @classmethod
    def get_versions(cls, appname, options=None):
        try:
            app = App.get_or_none(appname)
            availabe_meta_versions = app.availabe_meta_versions()
            return (200, AppApi.render_version_data(appname, availabe_meta_versions),
                    '', reverse('api_versions', kwargs={'appname': appname}))
        except NoAvailableImages, e:
            return (404, None, 'no avaible images for app %s:\n%s\nplease push images first.' % (appname, e),
                    reverse('api_versions', kwargs={'appname': appname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when getting version of app %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_repo', kwargs={'appname': appname}))


'''
这个类响应 console.views 的 对 Proc 相关的调用
'''


class ProcApi:

    @classmethod
    def render_pod_data(cls, pod):
        return {
            'containerid': pod['Containers'][0]['Id'],
            'containername': pod['Containers'][0]['Runtime']['Name'],
            'containerip': pod['Containers'][0]['ContainerIp'],
            'containerport': pod['Containers'][0]['ContainerPort'],
            'nodeip': pod['Containers'][0]['NodeIp'],
            'status': str(pod['Containers'][0]['Runtime']['State']['Running']),
            'uptime': convert_time_from_deployd(pod['Containers'][0]['Runtime']['State']['StartedAt']),
            'envs': pod['Containers'][0]['Runtime']['Config']['Env'],
        }

    @classmethod
    def render_proc_data(cls, appname, proc_lain_conf, proc_status=None, is_portal=False, client=None):
        data = {
            'procname': proc_lain_conf.name,
            'proctype': proc_lain_conf.type.name,
            'image': proc_lain_conf.image,
            'numinstances': proc_lain_conf.num_instances,
            'cpu': proc_lain_conf.cpu,
            'memory': proc_lain_conf.memory,
            'persistentdirs': proc_lain_conf.volumes,
            'dnssearchs': proc_lain_conf.dns_search,
            'ports': [{'portnumber': p.port, 'porttype': p.type.name} for p in proc_lain_conf.port.values()],
            'mountpoints': proc_lain_conf.mountpoint,
            'httpsonly': proc_lain_conf.https_only,
            'user': proc_lain_conf.user,
            'workingdir': proc_lain_conf.working_dir,
            'entrypoint': proc_lain_conf.entrypoint,
            'cmd': proc_lain_conf.cmd,
            'envs': proc_lain_conf.env,
            'pods': [],
            'depends': [],
            'url': reverse('api_proc', kwargs={'appname': appname, 'procname': proc_lain_conf.name}),
            'logs': proc_lain_conf.logs,
            'lasterror': '',
        }
        if proc_status and isinstance(proc_status['Status'], dict):
            pods, depends = [], []
            last_error = ''
            pods_meta = proc_status['Status']['Pods']
            if pods_meta is not None:
                # handle the situation when proc is portal
                if is_portal:
                    for client_name, pods_info in pods_meta.iteritems():
                        if client and client != client_name:
                            continue
                        for pod in pods_info:
                            pods.append(ProcApi.render_pod_data(pod))
                            last_error = pod['LastError']
                else:
                    for pod in pods_meta:
                        pods.append(ProcApi.render_pod_data(pod))
                    last_error = proc_status['Status']['LastError']
            data['pods'] = pods
            data['depends'] = depends
            data['lasterror'] = last_error
            # patch num_instances / cpu / memory spec in deploy to LainConf
            try:
                data['numinstances'] = proc_status[
                    'Status']['Spec']['NumInstances']
                data['cpu'] = int(proc_status['Status']['Spec'][
                                  'Pod']['Containers'][0]['CpuLimit'])
                data['memory'] = humanfriendly.format_size(
                    int(proc_status['Status']['Spec']['Pod']['Containers'][0]['MemoryLimit']))
                data['image'] = proc_status['Status'][
                    'Spec']['Pod']['Containers'][0]['Image']
            except:
                pass
        return data

    @classmethod
    def list_app_procs(cls, appname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))
            proc_datas = []
            for proc in app.lain_config.procs.values():
                if proc.type != ProcType.portal:
                    pg_status = app.podgroup_status("%s.%s.%s" % (
                        appname, proc.type.name, proc.name
                    ))
                    proc_datas.append(ProcApi.render_proc_data(
                        appname, proc, pg_status))
            return (200, proc_datas, '', reverse('api_procs', kwargs={'appname': appname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when get app %s procs:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_app', kwargs={'appname': appname}))

    @classmethod
    def create_app_proc(cls, appname, procname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))
            proc, pg_status = app.proc_and_pg_status(procname)
            if proc is None:
                return (400, None,
                        'no such proc %s in app %s' % (procname, appname),
                        reverse('api_procs', kwargs={'appname': appname}))
            if pg_status:
                return (409, ProcApi.render_proc_data(appname, proc, pg_status),
                        'proc with procname %s already exists\n' % procname,
                        reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))

            op_logger.info("DEPLOY: proc %s from app %s deployed by %s" % (
                procname, appname, AuthApi.operater))

            podgroup_name = "%s.%s.%s" % (
                app.appname, proc.type.name, proc.name)
            podgroup_spec = app.podgroup_spec(podgroup_name)
            deploy_result = recursive_deploy(podgroup_spec)
            if deploy_result.get("OK", False):
                return (201, ProcApi.render_proc_data(appname, proc, app.podgroup_status(podgroup_name)),
                        render_podgroup_deploy_result_to_msg(deploy_result),
                        reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
            else:
                return (500, None,
                        render_podgroup_deploy_result_to_msg(deploy_result),
                        reverse('api_procs', kwargs={'appname': appname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when create app %s proc %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, procname, e),
                    reverse('api_app', kwargs={'appname': appname}))

    @classmethod
    def get_app_proc(cls, appname, procname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))
            proc, pg_status = app.proc_and_pg_status(procname)
            if proc is None:
                return (404, None,
                        'no such proc %s in app %s' % (procname, appname),
                        reverse('api_procs', kwargs={'appname': appname}))
            if pg_status:
                return (200, ProcApi.render_proc_data(appname, proc, pg_status),
                        '', reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
            else:
                return (200, ProcApi.render_proc_data(appname, proc),
                        'proc %s exists but not deployed' % (procname),
                        reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when get app %s proc %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, procname, e),
                    reverse('api_procs', kwargs={'appname': appname}))

    @classmethod
    def update_app_proc(cls, appname, procname, options):
        def verify_options(options):
            num_instances_flag = None
            cpu_flag = None
            memory_flag = None
            msg = ''
            verified_options = {}
            if options.has_key('num_instances'):
                num_instances_flag = True
                num_instances = options['num_instances']
                if not isinstance(num_instances, int):
                    msg += 'invalid parameter: num_instances (%s) should be integer' % num_instances
                    num_instances_flag = False
                else:
                    verified_options['num_instances'] = num_instances
            if options.has_key('cpu'):
                cpu_flag = True
                cpu = options['cpu']
                if not isinstance(cpu, int):
                    msg += 'invalid parameter: cpu (%s) should be integer' % cpu
                    cpu_flag = False
                else:
                    verified_options['cpu'] = cpu
            if options.has_key('memory'):
                memory_flag = True
                memory = options['memory']
                try:
                    my_memory = humanfriendly.parse_size(memory)
                    verified_options['memory'] = my_memory
                except:
                    msg += 'invalid parameter: memory (%s) humanfriendly.parse_size(memory) failed' % memory
                    memory_flag = False
            ret_flag = all([
                len(verified_options),
                not(num_instances_flag is False),
                not(cpu_flag is False),
                not(memory_flag is False),
            ])
            if len(verified_options) == 0 and msg == '':
                msg = 'missing parameters: num_instances OR cpu OR memory'
            return ret_flag, msg, verified_options
        is_valid, msg, verified_options = verify_options(options)
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))

            if not is_valid:
                return (400, None, msg, reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
            if verified_options.has_key('num_instances') and len(verified_options) > 1:
                return (400, None, 'scale num_instances should be a separate operation', reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
            proc, pg_status = app.proc_and_pg_status(procname)
            if proc is None:
                return (404, None,
                        'no such proc %s in app %s' % (procname, appname),
                        reverse('api_procs', kwargs={'appname': appname}))
            if pg_status:
                now_podgroup_spec = render_podgroup_spec_from_json(
                    pg_status['Status']['Spec'])
                new_podgroup_spec = now_podgroup_spec.clone()
                if verified_options.has_key('num_instances'):
                    op_logger.info("SCALE: proc %s from app %s scaled by %s with instance %d" % (
                        procname, appname, AuthApi.operater, verified_options['num_instances']))
                    new_podgroup_spec.NumInstances = verified_options[
                        'num_instances']
                    deploy_result = app.podgroup_scale(new_podgroup_spec)
                else:  # should has_key('cpu') or has_key('memory')
                    # TODO
                    new_cpu = verified_options.get('cpu', None)
                    new_memory = verified_options.get('memory', None)
                    op_logger.info("SCALE: proc %s from app %s scaled by %s with memory %s, cpu %s" % (
                        procname, appname, AuthApi.operater, new_memory, new_cpu))
                    for c in new_podgroup_spec.Pod.Containers:
                        if new_cpu is not None:
                            c.CpuLimit = new_cpu
                        if new_memory is not None:
                            c.MemoryLimit = new_memory
                    deploy_result = app.podgroup_deploy(
                        new_podgroup_spec, autopatch=False)
                pg_status_new = app.podgroup_status(new_podgroup_spec.Name)
                if deploy_result.status_code < 400:
                    return (202, ProcApi.render_proc_data(appname, proc, pg_status_new),
                            render_op_result_to_msg(deploy_result),
                            reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
                else:
                    return (500, ProcApi.render_proc_data(appname, proc, pg_status_new),
                            render_op_result_to_msg(deploy_result),
                            reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
            else:
                return (400, ProcApi.render_proc_data(appname, proc),
                        'proc %s exists but not deployed\nplease deploy it first\n' % (
                            procname),
                        reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when scale app %s proc %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, procname, e),
                    reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))

    @classmethod
    def delete_app_proc(cls, appname, procname, options=None):
        try:
            app = App.get_or_none(appname)
            if not app.is_reachable():
                return (404, None,
                        'app with appname %s has not been deployd\n' % appname,
                        reverse('api_apps'))
            proc, pg_status = app.proc_and_pg_status(procname)
            if proc is None:
                return (404, None,
                        'no such proc %s in app %s' % (procname, appname),
                        reverse('api_procs', kwargs={'appname': appname}))
            if pg_status:
                op_logger.info("DELETE: proc %s from app %s deleted by %s" % (
                    procname, appname, AuthApi.operater))

                podgroup_name = "%s.%s.%s" % (
                    appname, proc.type.name, proc.name)
                remove_result = app.podgroup_remove(podgroup_name)
                if remove_result.status_code < 400:
                    return (202, ProcApi.render_proc_data(appname, proc),
                            render_podgroup_remove_result_to_msg(
                                remove_result),
                            reverse('api_procs', kwargs={'appname': appname}))
                else:
                    return (500, ProcApi.render_proc_data(appname, proc),
                            render_podgroup_remove_result_to_msg(
                                remove_result),
                            reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
            else:
                return (400, ProcApi.render_proc_data(appname, proc),
                        'proc %s exists but not deployed\nplease deploy it first\n' % (
                            procname),
                        reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))
        except Exception, e:
            client.captureException()
            return (500, None,
                    'fatal error when delete app %s proc %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, procname, e),
                    reverse('api_proc', kwargs={'appname': appname, 'procname': procname}))


'''
这个类响应 console.views 关于 maintainer 的所有调用
'''


class MaintainApi:

    @classmethod
    def render_maintainer_data(cls, appname, username, role):
        data = {
            'appname': appname,
            'username': username,
            'role': 'normal' if role == '' else role,
            'url': reverse('api_maintainers', kwargs={'appname': appname}),
        }
        return data

    @classmethod
    def render_role_data(cls, appname, username, role):
        data = {
            'role': 'normal' if role == '' else role,
        }
        return data

    @classmethod
    def add_maintainer(cls, access_token, appname, username, role):
        try:
            success, msg = Group.add_group_member(
                access_token, appname, username, role)
            if success:
                return (200, MaintainApi.render_maintainer_data(appname, username, role),
                        '', reverse('api_maintainers', kwargs={'appname': appname}))
            else:
                return (500, None,
                        'error adding maintainer of app %s : \n%s\n' % (
                            appname, msg),
                        reverse('api_docs'))
        except Exception, e:
            return (500, None,
                    'fatal error when adding maintainer for %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))

    @classmethod
    def delete_maintainer(cls, access_token, appname, username):
        try:
            success, msg = Group.delete_group_member(
                access_token, appname, username)
            if success:
                return (204, None, msg,
                        reverse('api_maintainers', kwargs={'appname': appname}))
            else:
                return (500, None,
                        'error deleting maintainer of app %s : \n%s\n' % (
                            appname, msg),
                        reverse('api_docs'))
        except Exception, e:
            return (500, None,
                    'fatal error when deleting maintainer for %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))

    @classmethod
    def get_maintainers(cls, access_token, appname):
        try:
            success, msg = Group.get_group_members(appname)
            if success:
                maintainer_datas = [MaintainApi.render_maintainer_data(
                    appname, maintainer['name'], maintainer['role']) for maintainer in msg]
                return (200, maintainer_datas,
                        '', reverse('api_maintainers', kwargs={'appname': appname}))
            else:
                return (500, None,
                        'error getting maintainer of app %s : \n%s\n' % (
                            appname, msg),
                        reverse('api_docs'))
        except Exception, e:
            return (500, None,
                    'fatal error when getting maintainer for %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))

    @classmethod
    def get_maintainer(cls, access_token, appname, username):
        try:
            success, msg = Group.get_group_members(appname)
            if success:
                for maintainer in msg:
                    if maintainer['name'] == username:
                        return (200, MaintainApi.render_maintainer_data(appname, maintainer['name'], maintainer['role']),
                                '', reverse('api_maintainer', kwargs={'appname': appname, 'username': username}))
                return (404, None,
                        'user %s does not exist in the app %s\n' % (
                            username, appname),
                        reverse('api_maintainers', kwargs={'appname': appname}))
            else:
                return (500, None,
                        'error deleting maintainer of app %s : \n%s\n' % (
                            appname, msg),
                        reverse('api_docs'))
        except Exception, e:
            return (500, None,
                    'fatal error when getting maintainer for %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))

    @classmethod
    def get_role(cls, appname, access_token=None, username=None):
        try:
            if not AuthApi.need_auth(AUTH_TYPES['SSO']):
                return (200, MaintainApi.render_role_data(appname, username if username else '', 'admin'), '',
                        reverse('api_role', kwargs={'appname': appname, 'username': ''}) if not access_token else
                        reverse('api_roles', kwargs={'appname': appname}))

            if access_token and not username:
                username = Authorize.get_username(access_token)

            success, role = Group.get_user_role(username, appname)
            if success:
                return (200, MaintainApi.render_role_data(appname, username, role), '',
                        reverse('api_role', kwargs={'appname': appname, 'username': username}) if not access_token else
                        reverse('api_roles', kwargs={'appname': appname}))
            else:
                return (404, None,
                        'user %s does not exist in the maintainer list of app %s\n' % (
                            username, appname),
                        reverse('api_maintainers', kwargs={'appname': appname}))
        except Exception, e:
            return (500, None,
                    'fatal error when getting roles for %s:\n%s\nplease contact with admin of lain\n' % (
                        appname, e),
                    reverse('api_docs'))


'''
这个类响应 console.views 关于 resource 的所有调用
'''


class ResourceApi:

    @classmethod
    def list_resource_instances(cls, resourcename, options=None):
        try:
            instance_datas = []
            for instance in Resource.get_instances(resourcename):
                instance_datas.append(AppApi.render_app(instance))
            return (200, instance_datas, '', reverse('api_instances', kwargs={'resourcename': resourcename}))
        except Exception, e:
            return (500, None,
                    'fatal error when get resource %s instances:\n%s\nplease contact with admin of lain\n' % (
                        resourcename, e),
                    reverse('api_instances', kwargs={'resourcename': resourcename}))


'''
这个类响应 console.views 关于 auth 的所有调用
'''


class AuthApi:

    operater = "unknown"

    @classmethod
    def need_auth(cls, auth_type):
        return Authorize.need_auth(auth_type)

    @classmethod
    def get_auth_status(cls, auth_type):
        need_auth = Authorize.need_auth(auth_type)
        status = 'opened' if need_auth else 'closed'
        auth_status = {
            'status': status,
        }
        return auth_status

    @classmethod
    def verify_token(cls, access_token):
        return Authorize.verify_token(access_token)

    @classmethod
    def verify_app_access(cls, groups, appname):
        return Authorize.verify_app_access(groups, appname)

    @classmethod
    def get_sso_access_token(cls, code):
        return Authorize.get_sso_access_token(code)

    @classmethod
    def redirect_to_ui(cls, token_json):
        return Authorize.redirect_to_ui(token_json)

    @classmethod
    def authorize_registry(cls, request):
        return Authorize.authorize_registry(request)

    @classmethod
    def create_resource_instance_group(cls, access_token, appname):
        resources = App.get(appname).lain_config.use_resources
        if not resources:
            return True, 'no used resources'
        for resource_appname, resource_props in resources.iteritems():
            instance_name = resource_instance_name(resource_appname, appname)
            instance = App.get_or_none(instance_name)
            if not instance:
                instance = App.create(instance_name)
                success, msg = Group.create_group_for_resource_instance(
                    access_token, resource_appname, instance_name)
                if not success:
                    instance.delete()
                    return False, msg
        return True, 'create resource instance groups successfully!'


'''
这个类响应 apis.views 关于 config 的所有调用
'''


class ConfigApi:

    @classmethod
    def use_lvault(cls):
        return True

    @classmethod
    def construct_config_for_instance(cls, token, resource, instance):
        def get_resource_pg_name(resourcename, instance_pg_name):
            pg_list = instance_pg_name.split(".")[-2:]
            pg_list.insert(0, resourcename)
            return ".".join(pg_list)

        if not cls.use_lvault():
            return True
        for pg in instance.app_spec.PodGroups:
            pg_name = get_resource_pg_name(resource.appname, pg.Name)
            basic_image = pg.Pod.Containers[0].Image
            release_image = cls.construct_config(
                token, resource, pg_name, basic_image)
            pg.Pod.Containers[
                0].Image = release_image if release_image else basic_image

    @classmethod
    def construct_config_for_app(cls, token, app):
        if not cls.use_lvault():
            return
        for pg in app.app_spec.PodGroups:
            basic_image = pg.Pod.Containers[0].Image
            release_image = cls.construct_config(
                token, app, pg.Name, basic_image)
            pg.Pod.Containers[
                0].Image = release_image if release_image else basic_image

    @classmethod
    def construct_config(cls, token, app, pg_name, base_image):
        def get_defined_secret_files(app, pg_name):
            for proc in app.lain_config.procs.values():
                if "%s.%s.%s" % (app.appname, proc.type.name, proc.name) == pg_name:
                    return proc.secret_files

        defined_secret_files = get_defined_secret_files(app, pg_name)
        if len(defined_secret_files) == 0:
            return None

        config_list = Config.get_configs(token, app.appname, pg_name)
        config_list, timestamp = Config.validate_defined_secret_files(
            config_list, defined_secret_files)
        config_tag = cls.get_config_image(
            app, config_list, defined_secret_files, pg_name, timestamp)

        new_release_image = cls.gen_release_image(
            app, base_image, config_tag, len(config_list))
        return "%s/%s" % (PRIVATE_REGISTRY, new_release_image)

    @classmethod
    def get_config_image(cls, app, config_list, defined_secret_files, pg_name, timestamp):
        latest_config_tag = "%s-config-%s" % (
            pg_name.split(".")[-1], timestamp)
        if latest_config_tag not in app.registry_tags:
            Config.generate_config_image(
                config_list, defined_secret_files, app.appname, latest_config_tag)
        return latest_config_tag

    @classmethod
    def gen_release_image(cls, app, base_image, config_tag, config_layer_count):
        if not base_image.startswith(PRIVATE_REGISTRY):
            logger.error("base_image format wrong, should start with %s, in fact %s" % (
                PRIVATE_REGISTRY, base_image))
            raise Exception("base_image format wrong, should start with %s, in fact %s" % (
                PRIVATE_REGISTRY, base_image))

        base_image = base_image[len(PRIVATE_REGISTRY) + 1:]
        target_repo, target_tag = base_image.split(':')

        if target_repo != app.appname or "%s-%s" % (target_tag, config_tag) not in app.registry_tags:
            Config.overlap_config_image(
                app.appname, config_tag, config_layer_count, target_repo, target_tag)
        return "%s:%s-%s" % (target_repo, target_tag, config_tag)

class StreamrouterApi:

    @classmethod
    def list_ports(cls):
        resp = Streamrouter.get_streamrouter_ports()
        if resp == None:
            return (400, None, '', reverse('api_streamrouter'))
        else:
            return (200, resp, '', reverse('api_streamrouter'))
