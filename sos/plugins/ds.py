# Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os


class DirectoryServer(Plugin, RedHatPlugin):
    """Directory Server
    """

    plugin_name = 'ds'
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
        self.add_forbidden_path([
            "/etc/dirsrv/slapd*/pin.txt",
            "/etc/dirsrv/slapd*/key3.db",
            "/etc/dirsrv/slapd*/pwfile.txt",
            "/etc/dirsrv/slapd*/*passw*",
            "/etc/dirsrv/admin-serv/key[3-4].db",
            "/etc/dirsrv/admin-serv/admpw",
            "/etc/dirsrv/admin-serv/password.conf"
        ])

        try:
            for d in os.listdir("/etc/dirsrv"):
                if d[0:5] == 'slapd':
                    certpath = os.path.join("/etc/dirsrv", d)
                    self.add_cmd_output("certutil -L -d %s" % certpath)
        except OSError:
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
                "/etc/dirsrv/admin-serv",
                "/var/log/dirsrv/*"
            ])
        elif "ds7" in self.check_version():
            self.add_copy_spec([
                "/opt/redhat-ds/slapd-*/config",
                "/opt/redhat-ds/slapd-*/logs"
            ])

# vim: set et ts=4 sw=4 :
