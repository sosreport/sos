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

from sos.plugins import Plugin, RedHatPlugin


class VirtWho(Plugin, RedHatPlugin):
    """Virt-Who agent
    """

    plugin_name = 'virtwho'
    profiles = ('virt', 'system')
    packages = ('virt-who',)

    def setup(self):
        self.add_copy_spec("/etc/virt-who.d/*")

    def postproc(self):
        self.do_path_regex_sub(r"\/etc\/virt-who\.d",
                               r"(.*password=)(\S*)",
                               r"\1********")

# vim: set et ts=4 sw=4 :
