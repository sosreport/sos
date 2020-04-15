# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OpenDaylight(Plugin, RedHatPlugin):

    short_desc = 'OpenDaylight network manager'

    plugin_name = 'opendaylight'
    profiles = ('openstack', 'openstack_controller')

    packages = ('opendaylight', 'puppet-opendaylight')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/opendaylight"

    def setup(self):
        self.add_copy_spec([
            "/opt/opendaylight/etc/",
            self.var_puppet_gen + "/opt/opendaylight/etc/",
        ])

        if self.get_option("all_logs"):

            # Oxygen-SR3 and earlier versions, and may be removed in a future
            # update.

            self.add_copy_spec([
                "/opt/opendaylight/data/log/",
            ])

        else:

            # Oxygen-SR3 and earlier versions, and may be removed in a future
            # update.

            self.add_copy_spec([
                "/opt/opendaylight/data/log/*.log*",
            ])

        self.add_cmd_output("docker logs opendaylight_api")

# vim: set et ts=4 sw=4 :
