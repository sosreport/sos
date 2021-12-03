# Copyright (C) 2021 Mirntis, Inc., Oleksii Molchanov <omolchanov@mirantis.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class OpenContrail(Plugin, IndependentPlugin):
    short_desc = "OpenContrail SDN"
    plugin_name = 'opencontrail'
    profiles = ("network",)
    packages = ('opencontrail',)
    containers = ('opencontrail.*',)

    def setup(self):
        # assuming the container names will start with "opencontrail"
        in_container = self.container_exists('opencontrail.*')
        if in_container:
            cnames = self.get_containers(get_all=True)
            cnames = [c[1] for c in cnames if 'opencontrail' in c[1]]
            for cntr in cnames:
                self.add_cmd_output('contrail-status', container=cntr)
        else:
            self.add_cmd_output("contrail-status")

        self.add_cmd_output("vif --list")

        self.add_copy_spec([
            "/etc/contrail/*",
            "/var/log/contrail/*",
        ])

# vim: set et ts=4 sw=4 :
