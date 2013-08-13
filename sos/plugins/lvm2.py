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
                  ("lvmdump-am", 'use the -a -m options of lvmdump ' \
                    '(implies the "lvmdump" option)', 'slow', False)]

    def do_lvmdump(self):
        """Collects an lvmdump in standard format with optional metadata
           archives for each physical volume present.
        """
        lvmdump_cmd = "lvmdump -d '%s'"
        cmd = lvmdump_cmd % os.path.join(self.get_cmd_dir(), "lvmdump")
        if self.get_option('lvmdump-a'):
          cmd += " -a"
        self.add_cmd_output(cmd)

    def setup(self):
        self.add_cmd_output("vgdisplay -vv", root_symlink = "vgdisplay")
        self.add_cmd_output("vgscan -vvv")
        self.add_cmd_output("pvscan -v")
        self.add_cmd_output("pvs -a -v")
        self.add_cmd_output("vgs -v")
        self.add_cmd_output("lvs -a -o +devices")

        self.add_copy_spec("/etc/lvm")

        if self.get_option('lvmdump'):
            self.do_lvmdump()


