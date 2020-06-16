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
    """Red Hat Satellite 6"""

    cluster_name = 'Red Hat Satellite 6'
    packages = ('satellite', 'satellite-installer')

    def _psql_cmd(self, query):
        _cmd = "su postgres -c %s"
        _dbcmd = "psql foreman -c %s"
        return _cmd % quote(_dbcmd % quote(query))

    def get_nodes(self):
        cmd = self._psql_cmd('copy (select name from smart_proxies) to stdout')
        res = self.exec_master_cmd(cmd, need_root=True)
        if res['status'] == 0:
            nodes = [
                n.strip() for n in res['stdout'].splitlines()
                if 'could not change directory' not in n
            ]
            return nodes
        return []

    def set_node_label(self, node):
        if node.address == self.master.address:
            return 'satellite'
        return 'capsule'
