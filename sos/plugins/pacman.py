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

from sos.plugins import Plugin


class Pacman(Plugin):
    """ Pacman specific information
    """

    plugin_name = 'pacman'
    profiles = ('system', 'sysmgmt', 'packagemanager')
    packages = ('pacman',)

    def setup(self):
        self.add_copy_spec([
            "/etc/pacman.conf",
            "/etc/makepkg.conf"
        ])

        self.add_cmd_output(
            "ls -l /usr/share/libalpm/hooks /etc/pacman.d/hooks",
            suggest_filename="hooks")
        self.add_cmd_output([
            "checkupdates",
            "pacdiff --output",
            "pacman --query",
            "paccache --dryrun"
        ])

# vim: set et ts=4 sw=4 :
