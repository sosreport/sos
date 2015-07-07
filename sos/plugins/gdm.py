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
from sos.plugins.utilities import journalctl_commands


class Gdm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """GNOME display manager
    """

    plugin_name = 'gdm'
    profiles = ('desktop',)

    def setup(self):
        self.add_copy_spec("/etc/gdm/*")
        self.add_cmd_output([
            "systemctl status gdm.service"
        ])
        cmds = journalctl_commands(["--unit=gdm"], self.get_option("all_logs"))
        self.add_cmd_output([" ".join(x) for x in cmds])

# vim: set et ts=4 sw=4 :
