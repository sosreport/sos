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


class Anacron(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Anacron job scheduling service"""

    plugin_name = 'anacron'
    profiles = ('system',)

    # anacron may be provided by anacron, cronie-anacron etc.
    # just look for the configuration file which is common
    files = ('/etc/anacrontab',)

# vim: set et ts=4 sw=4 :
