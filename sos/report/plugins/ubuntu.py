# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Ubuntu(Plugin, UbuntuPlugin):

    short_desc = 'Ubuntu specific information'

    plugin_name = 'ubuntu'
    profiles = ('system',)

    def setup(self):
        self.add_cmd_output([
            "ubuntu-security-status --thirdparty --unavailable",
            "hwe-support-status --verbose",
        ])

        if self.is_installed('ubuntu-advantage-tools'):
            self.add_cmd_output("ubuntu-advantage status")
            if not self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/log/ubuntu-advantage.log",
                    "/var/log/ubuntu-advantage.log.1",
                    "/var/log/ubuntu-advantage.log.2*",
                ])
            else:
                self.add_copy_spec("/var/log/ubuntu-advantage.log*")
