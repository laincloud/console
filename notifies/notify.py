# -*- coding: utf-8

import json
import requests
from commons.utils import get_etcd_value, set_value_to_etcd
from commons.settings import ETCD_AUTHORITY, CONSOLE_NOTIFIES_PREFIX, IMAGE_PUSH_KEY, NOTIFIES_TYPES
from log import logger


def send_request(method, path, body, headers):
    return requests.request(method, path, headers=headers, json=body, timeout=10)


def image_push_notify(payload):
    image_push_key = CONSOLE_NOTIFIES_PREFIX + '/' + IMAGE_PUSH_KEY
    v = get_etcd_value(image_push_key, ETCD_AUTHORITY, default='[]')
    notifies = json.loads(v)
    headers = {"Content-type": "application/json"}
    for notify in notifies:
        try:
            logger.info('image_push_notify: %s' % notify)
            send_request("POST", notify, payload, headers)
        except Exception:
            pass


def fetch_notifies(notify_type):
    notifykey = NOTIFIES_TYPES.get(notify_type, '')
    if notifykey == '':
        return None
    image_push_key = CONSOLE_NOTIFIES_PREFIX + '/' + notifykey
    try:
        v = get_etcd_value(image_push_key, ETCD_AUTHORITY, default='[]')
        notifies = json.loads(v)
    except Exception:
        return None
    return notifies


def add_notifies(notify_type, notify_url):
    notifykey = NOTIFIES_TYPES.get(notify_type, '')
    if notifykey == '':
        return None
    image_push_key = CONSOLE_NOTIFIES_PREFIX + '/' + notifykey
    try:
        v = get_etcd_value(image_push_key, ETCD_AUTHORITY, default='[]')
        notifies = json.loads(v)
        notifies.append(notify_url)
        set_value_to_etcd(image_push_key, json.dumps(notifies), ETCD_AUTHORITY)
    except Exception:
        return None
    return notify_url


def delete_notifies(notify_type, notify_url):
    notifykey = NOTIFIES_TYPES.get(notify_type, '')
    if notifykey == '':
        return None
    image_push_key = CONSOLE_NOTIFIES_PREFIX + '/' + notifykey
    try:
        v = get_etcd_value(image_push_key, ETCD_AUTHORITY, default='[]')
        notifies = json.loads(v)
        i = notifies.index(notify_url)
        del notifies[i]
        set_value_to_etcd(image_push_key, json.dumps(notifies), ETCD_AUTHORITY)
    except Exception:
        return None
    return notify_url
