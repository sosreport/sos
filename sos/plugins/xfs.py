# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from six.moves import zip


class Xfs(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """XFS filesystem
    """

    plugin_name = 'xfs'
    profiles = ('storage',)

    option_list = [("logprint", 'gathers the log information', 'slow', False)]

    def setup(self):
        mounts = '/proc/mounts'
        ext_fs_regex = r"^(/dev/.+).+xfs\s+"
        for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
            for e in dev:
                parts = e.split(' ')
                self.add_cmd_output("xfs_info %s" % (parts[1]))

        if self.get_option('logprint'):
            for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
                for e in dev:
                    parts = e.split(' ')
                    self.add_cmd_output("xfs_logprint -c %s" % (parts[0]))

# vim: set et ts=4 sw=4 :
