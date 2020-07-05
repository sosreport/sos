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
            "ubuntu-advantage status"
        ])
