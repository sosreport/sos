# Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class PowerPath(Plugin, RedHatPlugin):

    short_desc = 'EMC PowerPath'

    plugin_name = 'powerpath'
    profiles = ('storage', 'hardware')
    packages = ('EMCpower',)
    kernel_mods = ('emcp', 'emcpdm', 'emcpgpx', 'emcpmpx')

    def get_pp_files(self):
        """ EMC PowerPath specific information - files
        """
        self.add_cmd_output("powermt version")
        self.add_copy_spec([
            "/etc/init.d/PowerPath",
            "/etc/powermt.custom",
            "/etc/emcp_registration",
            "/etc/emc/mpaa.excluded",
            "/etc/emc/mpaa.lams",
            "/etc/emcp_devicesDB.dat",
            "/etc/emcp_devicesDB.idx",
            "/etc/emc/powerkmd.custom",
            "/etc/modprobe.conf.pp"
        ])

    def get_pp_config(self):
        """ EMC PowerPath specific information - commands
        """
        self.add_cmd_output([
            "powermt display",
            "powermt display dev=all",
            "powermt check_registration",
            "powermt display options",
            "powermt display ports",
            "powermt display paths",
            "powermt dump"
        ])

    def setup(self):
        self.get_pp_files()
        # If PowerPath is running collect additional PowerPath specific
        # information
        if self.path_isdir("/proc/emcp"):
            self.get_pp_config()

# vim: set et ts=4 sw=4 :
