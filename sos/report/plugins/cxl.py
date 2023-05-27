# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class cxl(Plugin, IndependentPlugin):
    """This plugin collects data from Compute Express Link (CXL) devices
    """

    short_desc = 'Compute Express Link (CXL)'
    plugin_name = 'cxl'
    profiles = ('storage', 'hardware', 'memory')
    # Utilities can be installed by package or self compiled
    packages = ('cxl-cli', 'daxctl')
    commands = ('cxl', 'daxctl')

    def setup(self):
        """ Use the daxctl-list(1) command to collect disabled, devices,
        mapping, and region information

        Output is JSON formatted
        """
        self.add_cmd_output([
            "daxctl version",
            "daxctl list",
            "daxctl list -iDRM"
        ])

        """ Use the cxl-list(1) command to collect data about
        all CXL devices.

        Output is JSON formatted
        """
        self.add_cmd_output([
            "cxl version",
            "cxl list",
            "cxl list -vvv"
        ])

# vim: set et ts=4 sw=4 :
