# Copyright Red Hat 2022, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import yaml

from sos.collector.clusters import Cluster

INVENTORY = "/var/lib/mistral/overcloud/tripleo-ansible-inventory.yaml"


class rhosp(Cluster):
    """
    This cluster profile is for use with Red Hat OpenStack Platform
    environments.

    Different types of nodes may be enumerated by toggling the various profile
    options such as Controllers and Compute nodes. By default, only Controller
    nodes are enumerated.

    Node enumeration is done by inspecting the ansible inventory file used for
    deployment of the environment. This is canonically located at
    /var/lib/mistral/overcloud/tripleo-ansible-inventory.yaml. Similarly, the
    presence of this file on the primary node is what triggers the automatic
    enablement of this profile.

    Special consideration should be taken for where `sos collect` is being run
    from, in that the hostnames of the enumerated nodes must be resolveable
    from that system - not just from the primary node from which those nodes
    are discovered. If this is not possible, consider enabling the `use-ip`
    cluster option to instead have this profile source the IP addresses of the
    nodes in question.
    """

    cluster_name = 'Red Hat OpenStack Platform'
    option_list = [
        ('use-ip', False, 'use IP addresses instead of hostnames to connect'),
        ('controller', True, 'collect reports from controller nodes'),
        ('compute', False, 'collect reports from compute nodes')
    ]

    def check_enabled(self):
        return self.primary.file_exists(INVENTORY, need_root=True)

    def get_nodes(self):
        _nodes = []
        _addr_field = ('external_ip' if self.get_option('use-ip') else
                       'ctlplane_hostname')
        try:
            _inv = yaml.safe_load(self.primary.read_file(INVENTORY))
        except Exception as err:
            self.log_info("Error parsing yaml: %s" % err)
            raise Exception("Could not parse yaml for node addresses")
        try:
            for _t in ['Controller', 'Compute']:
                # fields are titled in the yaml, but our opts are lowercase
                if self.get_option(_t.lower()):
                    for host in _inv[_t]['hosts'].keys():
                        _nodes.append(_inv[_t]['hosts'][host][_addr_field])
        except Exception as err:
            self.log_error("Error getting %s host addresses: %s" % (_t, err))
        return _nodes
