### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Lvm2(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """lvm2 related information 
    """

    plugin_name = 'lvm2'

    option_list = [("lvmdump", 'collect an lvmdump tarball', 'fast', False),
                  ("lvmdump-am", 'attempt to collect an lvmdump with advanced ' \
                    + 'options and raw metadata collection', 'slow', False)]

    def do_lvmdump(self, metadata=False):
        """Collects an lvmdump in standard format with optional metadata
           archives for each physical volume present.
        """
        lvmdump_cmd = "lvmdump %s -d '%s'" 
        lvmdump_opts = ""
        if metadata:
            lvmdump_opts = "-a -m"
        cmd = lvmdump_cmd % (lvmdump_opts,
                             self.get_cmd_output_path(name="lvmdump"))
        self.add_cmd_output(cmd)

    def setup(self):
        self.add_cmd_output("vgdisplay -vv", root_symlink = "vgdisplay")
        self.add_cmd_outputs([
            "vgscan -vvv",
            "pvscan -v",
            "pvs -a -v",
            "vgs -v",
            "lvs -a -o +devices"
        ])

        self.add_copy_spec("/etc/lvm")

        if self.get_option('lvmdump'):
            self.do_lvmdump()
        elif self.get_option('lvmdump-am'):
            self.do_lvmdump(metadata=True)



# vim: et ts=4 sw=4
