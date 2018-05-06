# Copyright (C) 2007-2018 Red Hat, Inc. All rights reserved.
#
# Contributors:
# Kent Lamb <klamb@redhat.com>
# Marc Sauton <msauton@redhat.com>
# Pierre Carrier <pcarrier@redhat.com>
# Brian Gribble <bgribble@redhat.com
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further
# information.

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists
from glob import glob
import os


class CertificateSystem(Plugin, RedHatPlugin):
    """Certificate System and Dogtag
    """

    plugin_name = 'cs'
    profiles = ('identity', 'security')

    packages = (
        "redhat-cs",
        "rhpki-common",
        "pki-common",
        "redhat-pki",
        "dogtag-pki",
        "pki-base"
    )

    files = (
        "/opt/redhat-cs",
        "/usr/share/java/rhpki",
        "/usr/share/java/pki"
    )

    def checkversion(self):
        if self.is_installed("redhat-cs") or exists("/opt/redhat-cs"):
            return 71
        elif self.is_installed("rhpki-common") or \
                len(glob("/var/lib/rhpki-*")):
            return 73
        # 8 should cover dogtag
        elif self.is_installed("pki-common"):
            return 8
        elif self.is_installed("redhat-pki") or \
                self.is_installed("dogtag-pki") or \
                self.is_installed("pki-base"):
            return 9
        return False

    def setup(self):
        csversion = self.checkversion()
        self.limit = self.get_option("log_size")

        if not csversion:
            self.add_alert("Red Hat Certificate System not found.")
            return

        if csversion == 71:
            # Grab all logs.
            if self.get_option("all_logs"):
                self.add_copy_spec([
                    "/opt/redhat-cs/slapd-*/logs/",
                    "/opt/redhat-cs/cert-*/access",
                    "/opt/redhat-cs/cert-*/errors",
                    "/opt/redhat-cs/cert-*/system",
                    "/opt/redhat-cs/cert-*/transactions"
                    "/opt/redhat-cs/cert-*/debug",
                    "/opt/redhat-cs/cert-*/tps-debug.log"
                ])

            # Grab logs for each subsystem.
            self.add_copy_spec([
                "/opt/redhat-cs/slapd-*/logs/access",
                "/opt/redhat-cs/slapd-*/logs/errors",
                "/opt/redhat-cs/cert-*/access",
                "/opt/redhat-cs/cert-*/errors",
                "/opt/redhat-cs/cert-*/system",
                "/opt/redhat-cs/cert-*/transactions",
                "/opt/redhat-cs/cert-*/debug",
                "/opt/redhat-cs/cert-*/tps-debug.log"
            ], sizelimit=self.limit)

            # Grab configs for each subsystem.
            self.add_copy_spec([
                "/opt/redhat-cs/slapd-*/config/dse.ldif",
                "/opt/redhat-cs/cert-*/config/CS.cfg"
            ], sizelimit=self.limit)

        if csversion == 73:
            # Grab all logs.
            if self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/lib/rhpki-*/logs/"
                ])

            # Grab logs for each subsystem.
            self.add_copy_spec([
                "/var/lib/rhpki-*/logs/debug",
                "/var/lib/rhpki-*/logs/catalina.*",
                "/var/lib/rhpki-*/logs/ra-debug.log",
                "/var/lib/rhpki-*/logs/transactions",
                "/var/lib/rhpki-*/logs/system"
            ], sizelimit=self.limit)

            # Grab configs for each subsystem.
            self.add_copy_spec([
                "/var/lib/rhpki-*/conf/*cfg*",
                "/var/lib/rhpki-*/conf/*.ldif",
            ], sizelimit=self.limit)

        if csversion == 8:
            # Files containing sensitive information.
            self.add_forbidden_path("/etc/pki-*/password.conf")
            self.add_forbidden_path("/var/lib/pki-*/alias/key3.db")

            # Get certificates from CA.
            self.add_cmd_output([
                "certutil -L -d /var/lib/pki-*/alias"
            ])

            # Grab all logs.
            if self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/log/pki-*/",
                    "/var/log/pki-*-install.log"
                ])

            # Grab logs for each subsystem.
            self.add_copy_spec([
                "/var/log/pki-*/debug",
                "/var/log/pki-*/catalina.*",
                "/var/log/pki-*/ra-debug.log",
                "/var/log/pki-*/transactions",
                "/var/log/pki-*/system"
            ], sizelimit=self.limit)

            # Grab configs for each subsystem.
            self.add_copy_spec([
                "/etc/pki-*/",
                "/var/lib/pki-*/",
            ], sizelimit=self.limit)

        if csversion == 9:
            for dirs in os.listdir("/var/lib/pki"):
                # Files containing sensitive information.
                self.add_forbidden_path("/etc/pki/%s/password.conf" % dirs)
                self.add_forbidden_path("/etc/pki/%s/alias/key3.db" % dirs)

                # Get certificates from CA.
                self.add_cmd_output([
                    "certutil -L -d /etc/pki/%s/alias" % dirs
                ])

                # Grab all logs.
                if self.get_option("all_logs"):
                    self.add_copy_spec([
                        "/var/log/pki/%s" % dirs,
                        "/var/log/pki/pki-*-spawn.*"
                    ])

                # Grab logs for each subsystem.
                for subsystem in ("ca", "kra", "ocsp", "tks", "tps"):
                    self.add_copy_spec([
                        "/var/log/pki/" + dirs + "/catalina.*",
                        "/var/log/pki/" + dirs + "/host-manager.*",
                        "/var/log/pki/" + dirs + "/localhost.*",
                        "/var/log/pki/" + dirs + "/manager.*",
                        "/var/log/pki/" + dirs + "/" + subsystem + "/debug",
                        "/var/log/pki/" + dirs + "/"
                                        + subsystem + "/selftests",
                        "/var/log/pki/" + dirs + "/" + subsystem + "/system"
                    ], sizelimit=self.limit)

                # Grab configs for each subsystem.
                self.add_copy_spec([
                    "/var/lib/pki/%s" % dirs,
                    "/etc/pki/%s" % dirs
                ])

    # Obfuscate passwords in CS 8/9 tomcat files.
    def postproc(self):
        csversion = self.checkversion()
        serverXmlPasswordAttributes = ['keyPass', 'keystorePass',
                                       'truststorePass', 'SSLPassword']
        if csversion == 8:
            for attr in serverXmlPasswordAttributes:
                self.do_path_regex_sub(
                    r"\/etc\/pki-.*\/server.xml",
                    r"%s=(\S*)" % attr,
                    r'%s="********"' % attr
                )

            self.do_path_regex_sub(
                r"\/etc\/pki-.*\/tomcat-users.xml",
                r"password=(\S*)",
                r'password="********"'
            )

        if csversion == 9:
            for dirs in os.listdir("/var/lib/pki"):
                for attr in serverXmlPasswordAttributes:
                    self.do_path_regex_sub(
                        r"\/etc\/pki\/" + dirs + "\/server.xml",
                        r"%s=(\S*)" % attr,
                        r'%s="********"' % attr
                    )

                self.do_path_regex_sub(
                    r"\/etc\/pki\/" + dirs + "\/tomcat-users.xml",
                    r"password=(\S*)",
                    r'password="********"'
                )

# vim: set et ts=4 sw=4 :
