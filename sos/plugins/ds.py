# Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin
import os


class DirectoryServer(Plugin, RedHatPlugin):
    """Directory Server
    """

    plugin_name = 'directoryserver'
    profiles = ('identity',)

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
        self.add_forbidden_path("/etc/dirsrv/slapd*/pin.txt")
        self.add_forbidden_path("/etc/dirsrv/slapd*/key3.db")
        self.add_forbidden_path("/etc/dirsrv/slapd*/pwfile.txt")
        self.add_forbidden_path("/etc/dirsrv/slapd*/*passw*")
        self.add_forbidden_path("/etc/dirsrv/admin-serv/key3.db")
        self.add_forbidden_path("/etc/dirsrv/admin-serv/admpw")
        self.add_forbidden_path("/etc/dirsrv/admin-serv/password.conf")
        try:
            for d in os.listdir("/etc/dirsrv"):
                if d[0:5] == 'slapd':
                    certpath = os.path.join("/etc/dirsrv", d)
                    self.add_cmd_output("certutil -L -d %s" % certpath)
        except:
            self._log_warn("could not list /etc/dirsrv")

        if not self.check_version():
            self.add_alert("Directory Server not found.")
        elif "ds8" in self.check_version():
            self.add_copy_spec([
                "/etc/dirsrv/slapd*/cert8.db",
                "/etc/dirsrv/slapd*/certmap.conf",
                "/etc/dirsrv/slapd*/dse.ldif",
                "/etc/dirsrv/slapd*/dse.ldif.startOK",
                "/etc/dirsrv/slapd*/secmod.db",
                "/etc/dirsrv/slapd*/schema/*.ldif",
                "/var/log/dirsrv/*"
            ])
        elif "ds7" in self.check_version():
            self.add_copy_spec([
                "/opt/redhat-ds/slapd-*/config",
                "/opt/redhat-ds/slapd-*/logs"
            ])

# vim: set et ts=4 sw=4 :
