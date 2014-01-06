# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
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

class Maas(Plugin, UbuntuPlugin):
    """MAAS Plugin
    """

    plugin_name = 'maas'

    def setup(self):
        self.add_copy_specs([
            "/etc/squid-deb-proxy",
            "/etc/maas",
            "/var/lib/maas/dhcp*",
            "/var/log/apache2*",
            "/var/log/maas*",
        ])
        self.add_cmd_output("apt-cache policy maas-*")
        self.add_cmd_output("apt-cache policy python-django-*")
        self.add_cmd_output("maas dumpdata")
