## Copyright (C) 2007 Red Hat, Inc., Pierre Carrier <pcarrier@redhat.com>

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

class sssd(Plugin):
    """sssd-related Diagnostic Information
    """

    plugin_name = "sssd"
    packages = ('sssd',)

    def setup(self):
        self.add_copy_specs(["/etc/sssd", "/var/log/sssd/*"])

class RedHatSssd(sssd, RedHatPlugin):
    """sssd-related Diagnostic Information on Red Hat based distributions
    """

    def setup(self):
        super(RedHatSssd, self).setup()

class DebianSssd(sssd, DebianPlugin, UbuntuPlugin):
    """sssd-related Diagnostic Information on Debian based distributions
    """

    def setup(self):
        super(DebianSssd, self).setup()
        self.add_copy_specs(["/etc/default/sssd"])
