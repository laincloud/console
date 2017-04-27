# -*- coding: utf-8

import os
import uuid
import shutil
import requests
import subprocess
from docker import Client
from commons.settings import (LVAULT_CONFIG_URL, DOCKER_BASE_URL,
                              PRIVATE_REGISTRY, RFP_BIN)
from log import logger


cli = Client(base_url=DOCKER_BASE_URL)
CURRENT_FOLDER = os.path.abspath(os.path.dirname(__file__))
CONFIG_FOLDER = 'docker'

LVAULT_CONNECT_TIMEOUT = 3
LVAULT_READ_TIMEOUT = 20


def get_config_content(access_token, appname, procname):
    url = "%s?app=%s&proc=%s" % (LVAULT_CONFIG_URL, appname, procname)
    headers = {'access-token': access_token}
    logger.info("access lvaule for config : %s" % url)
    response = requests.get(url, headers=headers,
                            timeout=(LVAULT_CONNECT_TIMEOUT, LVAULT_READ_TIMEOUT))
    return response


def generate_tmp_folder():
    folder_name = str(uuid.uuid4())
    logger.info("generate tmp folder : %s" % folder_name)
    path = os.path.join(CURRENT_FOLDER, CONFIG_FOLDER, folder_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def validate_defined_secret_files(config_list, defined_secret_files):
    defined_config_list = [config for config in config_list
                           if config.path in defined_secret_files]

    if len(defined_config_list) == len(defined_secret_files):
        return True, defined_config_list
    else:
        return False, None


def generate_dockerfile(folder, config_list, defined_secret_files):
    def get_base():
        return "FROM scratch"

    def get_cmd(src, dest):
        return "\nCOPY %s %s" % (src, dest)

    dockerfile = get_base()
    for config in config_list:
        config_file = generate_config_file(folder, config)
        dockerfile += get_cmd(config_file, config.path)
    df = open(os.path.join(folder, 'Dockerfile'), 'w')
    df.write(dockerfile)
    df.close()


def generate_config_file(folder, config):
    filename = str(uuid.uuid4())
    config_file = os.path.join(folder, filename)
    f = open(config_file, 'w')
    f.write(config.content.encode('utf-8'))
    os.chmod(config_file, int(config.mode, 8))
    f.close()
    return filename


def generate_config_image(folder, appname, config_tag):
    tag = '%s/%s:%s' % (PRIVATE_REGISTRY, appname, config_tag)
    results = cli.build(path=folder, rm=True, tag=tag)
    for line in results:
        logger.info(line)


def remove_folder(folder):
    shutil.rmtree(folder)


def push_config_image(appname, config_tag):
    results = cli.push(
        repository="%s/%s" % (PRIVATE_REGISTRY, appname),
        tag=config_tag,
        insecure_registry=True
    )
    logger.info(results)


def overlap_layer_to_image(appname, cfg_tag, cfg_layer_count, sjwt, target_repo, target_tag, tjwt):
    logger.info("overlap %s:%s in %s to repo %s:%s in %s" % (
        appname, cfg_tag, PRIVATE_REGISTRY, target_repo, target_tag, PRIVATE_REGISTRY))

    cmd = "%s -srcReg=%s -srcRepo=%s -srcTag=%s -srcLayerCount=%s -srcJWT=%s \
    	   -targetReg=%s -targetRepo=%s -targetTag=%s -targetJWT=%s -newTag=%s" % (
        RFP_BIN,
        PRIVATE_REGISTRY,
        appname,
        cfg_tag,
        cfg_layer_count,
        sjwt,
        PRIVATE_REGISTRY,
        target_repo,
        target_tag,
        tjwt,
        "%s-%s" % (target_tag, cfg_tag)
    )
    logger.debug("overlap command is %s" % cmd)
    result_code = subprocess.call(cmd, shell=True)
    return result_code == 0
