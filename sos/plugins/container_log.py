# Copyright (C) 2019 Red Hat, Inc., Cedric Jeanneret <cjeanner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class ContainerLog(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """All container logs
    """
    plugin_name = 'container_log'
    logdir = '/var/log/containers/'
    files = (logdir, )

    def setup(self):
        if self.get_option('all_logs'):
            self.add_copy_spec(self.logdir)
        else:
            self.collect_subdirs()

    def collect_subdirs(self, root=logdir):
        """Collect *.log files from subdirs of passed root path
        """
        for dirName, _, _ in os.walk(root):
            self.add_copy_spec(os.path.join(dirName, '*.log'))

# vim: set et ts=4 sw=4 :
