# Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# Copyright (C) 2021 Red Hat, Inc., Mark Reynolds <mreynolds@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class DirectoryServer(Plugin, RedHatPlugin):

    short_desc = 'Directory Server'

    plugin_name = 'ds'
    profiles = ('identity',)

    files = ('/etc/dirsrv', '/opt/redhat-ds')
    packages = ('redhat-ds-base', 'redhat-ds-7')

    def check_version(self):
        if self.is_installed("redhat-ds-base") or \
                self.path_exists("/etc/dirsrv"):
            return "ds8"
        elif self.is_installed("redhat-ds-7") or \
                self.path_exists("/opt/redhat-ds"):
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
            for d in self.listdir("/etc/dirsrv"):
                if d[0:5] == 'slapd':
                    certpath = self.path_join("/etc/dirsrv", d)
                    self.add_cmd_output("certutil -L -d %s" % certpath)
                    self.add_cmd_output("dsctl %s healthcheck" % d)
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

        self.add_cmd_output("ls -l /var/lib/dirsrv/slapd-*/db/*")

    def postproc(self):
        # Example for scrubbing rootpw hash
        #
        # nsslapd-rootpw: AAAAB3NzaC1yc2EAAAADAQABAAABAQDeXYA3juyPqaUuyfWV2HuIM
        # v3gebb/5cvx9ehEAFF2yIKvsQN2EJGTV+hBM1DEOB4eyy/H11NqcNwm/2QsagDB3PVwYp
        # 9VKN3BdhQjlhuoYKhLwgtYUMiGL8AX5g1qxjirIkTRJwjbXkSNuQaXig7wVjmvXnB2o7B
        # zLtu99DiL1AizfVeZTYA+OVowYKYaXYljVmVKS+g3t29Obaom54ZLpfuoGMmyO64AJrWs
        #
        # to
        #
        # nsslapd-rootpw:********

        regexppass = r"(nsslapd-rootpw(\s)*:(\s)*)(\S+)([\r\n]\s.*)*\n"
        regexpkey = r"(nsSymmetricKey(\s)*::(\s)*)(\S+)([\r\n]\s.*)*\n"
        repl = r"\1********\n"
        self.do_path_regex_sub('/etc/dirsrv/*', regexppass, repl)
        self.do_path_regex_sub('/etc/dirsrv/*', regexpkey, repl)

# vim: set et ts=4 sw=4 :
