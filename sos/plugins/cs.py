# Copyright (C) 2007-2010 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
#                                        Marc Sauton <msauton@redhat.com>
#                                        Pierre Carrier <pcarrier@redhat.com>

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
from os.path import exists
from glob import glob


class CertificateSystem(Plugin, RedHatPlugin):
    """Certificate System and Dogtag
    """

    plugin_name = 'certificatesystem'
    profiles = ('identity', 'security')

    packages = (
        "redhat-cs",
        "rhpki-common",
        "pki-common"
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
        elif self.is_installed("pki-common") or exists("/usr/share/java/pki"):
            return 8
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

# vim: set et ts=4 sw=4 :
