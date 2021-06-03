# Copyright (C) 2007 Red Hat, Inc., Pierre Carrier <pcarrier@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, SoSPredicate)
from glob import glob


class Sssd(Plugin):

    short_desc = 'System security service daemon'

    plugin_name = "sssd"
    profiles = ('services', 'security', 'identity')
    packages = ('sssd', 'sssd-common')

    def setup(self):
        self.add_copy_spec([
            # main config file
            "/etc/sssd/sssd.conf",
            # SSSD 1.14
            "/etc/sssd/conf.d/*.conf",
            # dynamic Kerberos configuration
            "/var/lib/sss/pubconf/krb5.include.d/*"
        ])

        # add individual log files
        self.add_copy_spec(glob("/var/log/sssd/*log*"), tags='sssd_logs')

        # add memory cache
        self.add_copy_spec([
            "/var/lib/sss/mc/passwd",
            "/var/lib/sss/mc/group",
            "/var/lib/sss/mc/initgroups"
        ])

        # call sssctl commands only when sssd service is running,
        # otherwise the command timeouts
        sssd_pred = SoSPredicate(self, services=["sssd"])
        self.add_cmd_output("sssctl config-check", pred=sssd_pred)

        # if predicate fails, domain["status"] = None and thus we skip parsing
        # missing output
        domain = self.collect_cmd_output("sssctl domain-list", pred=sssd_pred)
        if domain['status'] == 0:
            for domain_name in domain['output'].splitlines():
                self.add_cmd_output("sssctl domain-status -o " + domain_name)

    def postproc(self):
        regexp = r"(\s*ldap_default_authtok\s*=\s*)\S+"

        self.do_file_sub("/etc/sssd/sssd.conf", regexp, r"\1********")
        self.do_path_regex_sub("/etc/sssd/conf.d/*", regexp, r"\1********")


class RedHatSssd(Sssd, RedHatPlugin):

    def setup(self):
        super(RedHatSssd, self).setup()


class DebianSssd(Sssd, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianSssd, self).setup()
        self.add_copy_spec("/etc/default/sssd")

# vim: set et ts=4 sw=4 :
