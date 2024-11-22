# Copyright (C) 2019 Red Hat, Inc., Cedric Jeanneret <cjeanner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class ContainerLog(Plugin, IndependentPlugin):

    short_desc = 'All logs under /var/log/containers'
    plugin_name = 'container_log'
    logdir = '/var/log/containers/'
    poddir = '/var/log/pods/'
    rotated_dirs = [poddir + '*/*.log.*', poddir + '*/*/*.log.*']
    files = (logdir, )

    option_list = [
        PluginOpt('rotated', default=False, val_type=bool,
                  desc='also get rotated logs from /var/log/pods'),
    ]

    def setup(self):
        if self.get_option('all_logs'):
            self.add_copy_spec(self.logdir)
            if self.get_option('rotated'):
                self.add_copy_spec(self.rotated_dirs)
        else:
            self.collect_subdirs(self.logdir, '*.log')
            if self.get_option('rotated'):
                self.collect_subdirs(self.poddir, '*.log.*')

    def collect_subdirs(self, root, glob):
        """Collect *.log files from subdirs of passed root path
        """
        for dir_name, _, _ in os.walk(root):
            self.add_copy_spec(self.path_join(dir_name, glob))

# vim: set et ts=4 sw=4 :
