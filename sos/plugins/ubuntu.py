# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin


class Ubuntu(Plugin, UbuntuPlugin):
    """ Ubuntu specific information
    """

    plugin_name = 'ubuntu'
    profiles = ('system',)

    option_list = [
        ('support-show-all',
         'Show all packages with their status', '', False),
    ]

    def setup(self):
        cmd = ["ubuntu-support-status"]

        if self.get_option('support-show-all'):
            cmd.append("--show-all")

        self.add_cmd_output(" ".join(cmd),
                            suggest_filename='ubuntu-support-status.txt')
