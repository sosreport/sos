# Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, os


class PowerPath(Plugin, RedHatPlugin):
    """ EMC PowerPath
    """

    plugin_name = 'powerpath'
    profiles = ('storage', 'hardware')
    packages = ('EMCpower',)

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
        if os.path.isdir("/proc/emcp"):
            self.get_pp_config()

# vim: set et ts=4 sw=4 :
