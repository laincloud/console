# -*- coding: utf-8

import configs.utils
from authorize.models import Authorize
from log import logger


class Secret:

    def __init__(self, path, content, timestamp, mode):
        self.path = self.get_absulute_path(path)
        self.content = content
        self.timestamp = timestamp
        self.mode = mode

    def get_absulute_path(self, path):
        path_list = path.split('/')[2:]
        return '/%s' % '/'.join(path_list)


class Config:
    """
        Config is used for getting secret files from lvault, 
        checking config files, generating config images, 
        pushing config images, and overlapping config images.
        If anything accident happened, raise Exception.
    """

    @classmethod
    def get_configs(cls, access_token, appname, procname):
        try:
            response = configs.utils.get_config_content(
                access_token, appname, procname)
            config_list = []
            if response.status_code != 200:
                cls.handle_error("fail get config file from lvault for app %s proc %s" % (
                    appname, procname))
            secret_files = response.json()
            for s in secret_files:
                config_list.append(
                    Secret(s['path'], s['content'], s['timestamp'], s['mode']))
            return config_list
        except Exception, e:
            cls.handle_error("Exception get configs from lvault for proc %s : %s" % (
                procname, str(e)))

    @classmethod
    def validate_defined_secret_files(cls, config_list, defined_secret_files):
        success, config_list = configs.utils.validate_defined_secret_files(
            config_list, defined_secret_files)
        if not success:
            cls.handle_error(
                "some defined secret files not exist in lvault, please check")
        latest_timestamp = 0
        for config in config_list:
            latest_timestamp = config.timestamp if config.timestamp > latest_timestamp \
                else latest_timestamp
        return config_list, latest_timestamp

    @classmethod
    def generate_config_image(cls, config_list, defined_secret_files, appname, config_tag):
        try:
            logger.info("ready generate config images %s for app %s" %
                        (config_tag, appname))
            folder = configs.utils.generate_tmp_folder()
            configs.utils.generate_dockerfile(
                folder, config_list, defined_secret_files)
            configs.utils.generate_config_image(folder, appname, config_tag)
            configs.utils.push_config_image(appname, config_tag)
        except Exception, e:
            cls.handle_error("error generating config images: %s" % str(e))
        finally:
            configs.utils.remove_folder(folder)

    @classmethod
    def overlap_config_image(cls, appname, config_tag, config_layer_count, target_repo, target_tag):
        sjwt = Authorize.get_jwt_with_appname(appname)
        tjwt = Authorize.get_jwt_with_appname(target_repo)
        success = configs.utils.overlap_layer_to_image(appname, config_tag, config_layer_count, sjwt,
                                                       target_repo, target_tag, tjwt)
        if not success:
            cls.handle_error("error overlapping config image from tag %s to repo %s, version %s" % (
                config_tag, target_repo, target_tag))
        else:
            logger.info("success overlapping config image from tag %s to repo %s, version %s" % (
                config_tag, target_repo, target_tag))

    @classmethod
    def handle_error(cls, msg):
        logger.error(msg)
        raise Exception(msg)
