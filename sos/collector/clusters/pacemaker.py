# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.collector.clusters import Cluster


class pacemaker(Cluster):

    cluster_name = 'Pacemaker High Availability Cluster Manager'
    sos_plugins = ['pacemaker']
    packages = ('pacemaker',)
    option_list = [
        ('online', True, 'Collect nodes listed as online'),
        ('offline', True, 'Collect nodes listed as offline')
    ]

    def get_nodes(self):
        self.res = self.exec_primary_cmd('pcs status')
        if self.res['status'] != 0:
            self.log_error('Cluster status could not be determined. Is the '
                           'cluster running on this node?')
            return []
        if 'node names do not match' in self.res['output']:
            self.log_warn('Warning: node name mismatch reported. Attempts to '
                          'connect to some nodes may fail.\n')
        return self.parse_pcs_output()

    def parse_pcs_output(self):
        nodes = []
        if self.get_option('online'):
            nodes += self.get_online_nodes()
        if self.get_option('offline'):
            nodes += self.get_offline_nodes()
        return nodes

    def get_online_nodes(self):
        for line in self.res['output'].splitlines():
            if line.startswith('Online:'):
                nodes = line.split('[')[1].split(']')[0]
                return [n for n in nodes.split(' ') if n]

    def get_offline_nodes(self):
        offline = []
        for line in self.res['output'].splitlines():
            if line.startswith('Node') and line.endswith('(offline)'):
                offline.append(line.split()[1].replace(':', ''))
            if line.startswith('OFFLINE:'):
                nodes = line.split('[')[1].split(']')[0]
                offline.extend([n for n in nodes.split(' ') if n])
        return offline

# vim: set et ts=4 sw=4 :
