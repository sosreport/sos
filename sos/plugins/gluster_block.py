# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import glob
from sos.plugins import Plugin, RedHatPlugin


class GlusterBlock(Plugin, RedHatPlugin):
    """Gluster Block"""

    plugin_name = 'gluster_block'
    profiles = ('storage',)
    packages = ("gluster-block",)
    files = ("/usr/sbin/gluster-block",)

    def setup(self):

        # collect logs - apply log_size for any individual file
        # all_logs takes precedence over logsize
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
        else:
            limit = 0

        if limit:
            for f in glob.glob("/var/log/gluster-block/*.log"):
                self.add_copy_spec(f, limit)
        else:
            self.add_copy_spec("/var/log/gluster-block")
