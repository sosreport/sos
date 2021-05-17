# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Hyperv(Plugin, IndependentPlugin):
    """Hyper-V client information"""

    short_desc = 'Microsoft Hyper-V client information'
    plugin_name = "hyperv"
    files = ('/sys/bus/vmbus/',)

    def setup(self):

        self.add_copy_spec([
            "/sys/bus/vmbus/drivers/",
            # copy devices/*/* instead of devices/ to follow link files
            "/sys/bus/vmbus/devices/*/*"
        ])

        self.add_cmd_output("lsvmbus -vv")

# vim: set et ts=4 sw=4 :
