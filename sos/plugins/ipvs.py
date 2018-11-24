# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class Ipvs(Plugin, RedHatPlugin, DebianPlugin):
    """Linux IP virtual server
    """

    plugin_name = 'ipvs'
    profiles = ('cluster', 'network')

    packages = ('ipvsadm',)

    def setup(self):
        self.add_cmd_output([
            "ipvsadm -Ln",
            "ipvsadm -Ln --connection",
            "ipvsadm -Ln --persistent-conn",
            "ipvsadm -Ln --rate",
            "ipvsadm -Ln --stats",
            "ipvsadm -Ln --thresholds",
            "ipvsadm -Ln --timeout"
        ])

# vim: set et ts=4 sw=4 :
