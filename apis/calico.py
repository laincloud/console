# -*- coding: utf-8

import pycalico.datastore_datatypes
import pycalico.datastore
from commons.settings import ETCD_AUTHORITY

pycalico.datastore.ETCD_AUTHORITY_DEFAULT = ETCD_AUTHORITY
calico_client = pycalico.datastore.DatastoreClient()


class CalicoException(Exception):
    pass


def calico_profile_rule_add(profile_name, rule_type, rule):
    """Add a single rule of type rules_type at the first position
    Args:
        rule_type may be "outbound_rules" or "inbound_rules"
    """
    if not calico_client.profile_exists(profile_name):
        calico_client.create_profile(profile_name)
    profile = calico_client.get_profile(profile_name)
    if rule_type == "inbound_rules":
        profile.rules[0].insert(0, rule)
    elif rule_type == "outbound_rules":
        profile.rules[1].insert(0, rule)
    else:
        raise CalicoException(
            "calico rule type must be inbound_rules or outbound_rules")
    calico_client.profile_update_rules(profile)


def calico_profile_rule_add_inbound_allow_from_tag_at_first(profile_name, tag):
    rule = pycalico.datastore_datatypes.Rule()
    rule['action'] = 'allow'
    rule['src_tag'] = tag
    calico_profile_rule_add(profile_name, "inbound_rules", rule)
