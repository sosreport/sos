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


class kubernetes(Cluster):

    cluster_name = 'Community Kubernetes'
    packages = ('kubernetes-master',)
    sos_plugins = ['kubernetes']
    sos_plugin_options = {'kubernetes.all': 'on'}

    cmd = 'kubectl'

    option_list = [
        ('label', '', 'Filter node list to those with matching label'),
        ('role', '', 'Filter node list to those with matching role')
    ]

    def get_nodes(self):
        self.cmd += ' get nodes'
        if self.get_option('label'):
            self.cmd += ' -l %s ' % quote(self.get_option('label'))
        res = self.exec_master_cmd(self.cmd)
        if res['status'] == 0:
            nodes = []
            roles = [x for x in self.get_option('role').split(',') if x]
            for nodeln in res['stdout'].splitlines()[1:]:
                node = nodeln.split()
                if not roles:
                    nodes.append(node[0])
                else:
                    if node[2] in roles:
                        nodes.append(node[0])
            return nodes
        else:
            raise Exception('Node enumeration did not return usable output')
