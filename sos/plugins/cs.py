# Copyright (C) 2007-2010 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
#                                        Marc Sauton <msauton@redhat.com>
#                                        Pierre Carrier <pcarrier@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists
from glob import glob


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

        if not csversion:
            self.add_alert("Red Hat Certificate System not found.")
            return
        if csversion == 71:
            self.add_copy_spec([
                "/opt/redhat-cs/slapd-*/logs/access",
                "/opt/redhat-cs/slapd-*/logs/errors",
                "/opt/redhat-cs/slapd-*/config/dse.ldif",
                "/opt/redhat-cs/cert-*/errors",
                "/opt/redhat-cs/cert-*/config/CS.cfg",
                "/opt/redhat-cs/cert-*/access",
                "/opt/redhat-cs/cert-*/errors",
                "/opt/redhat-cs/cert-*/system",
                "/opt/redhat-cs/cert-*/transactions",
                "/opt/redhat-cs/cert-*/debug",
                "/opt/redhat-cs/cert-*/tps-debug.log"
            ])
        if csversion == 73:
            self.add_copy_spec([
                "/var/lib/rhpki-*/conf/*cfg*",
                "/var/lib/rhpki-*/conf/*.ldif",
                "/var/lib/rhpki-*/logs/debug",
                "/var/lib/rhpki-*/logs/catalina.*",
                "/var/lib/rhpki-*/logs/ra-debug.log",
                "/var/lib/rhpki-*/logs/transactions",
                "/var/lib/rhpki-*/logs/system"
            ])
        if csversion in (73, 8):
            self.add_copy_spec([
                "/etc/dirsrv/slapd-*/dse.ldif",
                "/var/log/dirsrv/slapd-*/access",
                "/var/log/dirsrv/slapd-*/errors"
            ])
        if csversion == 8:
            self.add_copy_spec([
                "/etc/pki-*/CS.cfg",
                "/var/lib/pki-*/conf/*cfg*",
                "/var/log/pki-*/debug",
                "/var/log/pki-*/catalina.*",
                "/var/log/pki-*/ra-debug.log",
                "/var/log/pki-*/transactions",
                "/var/log/pki-*/system"
            ])
        if csversion == 9:
            # Get logs and configs for each subsystem if installed
            for subsystem in ('ca', 'kra', 'ocsp', 'tks', 'tps'):
                self.add_copy_spec([
                    "/var/lib/pki/*/" + subsystem + "/conf/CS.cfg",
                    "/var/lib/pki/*/logs/" + subsystem + "/system",
                    "/var/lib/pki/*/logs/" + subsystem + "/transactions",
                    "/var/lib/pki/*/logs/" + subsystem + "/debug",
                    "/var/lib/pki/*/logs/" + subsystem + "/selftests.log"
                ])

            # Common log files
            self.add_copy_spec([
                "/var/lib/pki/*/logs/catalina.*",
                "/var/lib/pki/*/logs/localhost*.log",
                "/var/lib/pki/*/logs/localhost*.txt",
                "/var/lib/pki/*/logs/manager*.log",
                "/var/lib/pki/*/logs/host-manager*.log",
                "/var/lib/pki/*/logs/tps/tokendb-audit.log"
            ])

# vim: set et ts=4 sw=4 :
