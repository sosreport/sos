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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import re
from six.moves import zip

class Filesys(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """information on filesystems
    """

    plugin_name = 'filesys'

    option_list = [("lsof", 'gathers information on all open files', 'slow', False),
                   ("dumpe2fs", 'dump filesystem information', 'slow', False)]

    def setup(self):
        self.add_copy_specs([
            "/proc/filesystems",
            "/etc/fstab",
            "/proc/self/mounts",
            "/proc/self/mountinfo",
            "/proc/self/mountstats",
            "/proc/mounts"
        ])
        self.add_cmd_output("mount -l", root_symlink = "mount")
        self.add_cmd_output("df -al", root_symlink = "df")
        self.add_cmd_output("df -ali")
        self.add_cmd_output("findmnt")

        if self.get_option('lsof'):
            self.add_cmd_output("lsof -b +M -n -l -P", root_symlink = "lsof")

        if self.get_option('dumpe2fs'):
            mounts = '/proc/mounts'
            ext_fs_regex = r"^(/dev/.+).+ext[234]\s+"
            for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
                self.add_cmd_output("dumpe2fs -h %s" % (dev))

# vim: et ts=4 sw=4
