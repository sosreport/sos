## Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

## This program is free software; you can redistribute it and/or modify
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

from sos.plugins import Plugin, RedHatPlugin
import os

class DirectoryServer(Plugin, RedHatPlugin):
    """Directory Server information
    """

    plugin_name = 'directoryserver'

    files = ('/etc/dirsrv', '/opt/redhat-ds')
    packages = ('redhat-ds-base', 'redhat-ds-7')

    def check_version(self):
        if self.is_installed("redhat-ds-base") or \
        os.path.exists("/etc/dirsrv"):
            return "ds8"
        elif self.is_installed("redhat-ds-7") or \
        os.path.exists("/opt/redhat-ds"):
            return "ds7"
        return False

    def setup(self):
        if not self.check_version():
            self.add_alert("Directory Server not found.")
        elif "ds8" in self.check_version():
            self.add_copy_specs([
                "/etc/dirsrv/slapd*",
                "/var/log/dirsrv/*"
            ])
        elif "ds7" in self.check_version():
            self.add_copy_specs([
                "/opt/redhat-ds/slapd-*/config",
                "/opt/redhat-ds/slapd-*/logs"
            ])

# vim: et ts=4 sw=4
