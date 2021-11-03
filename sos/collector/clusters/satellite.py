# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from pipes import quote
from sos.collector.clusters import Cluster


class satellite(Cluster):
    """
    This profile is specifically for Red Hat Satellite 6, and not earlier
    releases of Satellite.

    While note technically a 'cluster' in the traditional sense, Satellite
    does provide for 'capsule' nodes which is what this profile aims to
    enumerate beyond the 'primary' Satellite system.
    """

    cluster_name = 'Red Hat Satellite 6'
    packages = ('satellite', 'satellite-installer')

    def _psql_cmd(self, query):
        _cmd = "su postgres -c %s"
        _dbcmd = "psql foreman -c %s"
        return _cmd % quote(_dbcmd % quote(query))

    def get_nodes(self):
        cmd = self._psql_cmd('copy (select name from smart_proxies) to stdout')
        res = self.exec_primary_cmd(cmd, need_root=True)
        if res['status'] == 0:
            nodes = [
                n.strip() for n in res['output'].splitlines()
                if 'could not change directory' not in n
            ]
            return nodes
        return []

    def set_node_label(self, node):
        if node.address == self.primary.address:
            return 'satellite'
        return 'capsule'

# vim: set et ts=4 sw=4 :
