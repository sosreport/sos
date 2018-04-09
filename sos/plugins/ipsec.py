# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class IPSec(Plugin):
    """Internet protocol security
    """

    plugin_name = "ipsec"
    profiles = ('network',)
    packages = ('ipsec-tools',)


class RedHatIpsec(IPSec, RedHatPlugin):

    files = ('/etc/racoon/racoon.conf',)

    def setup(self):
        self.add_copy_spec("/etc/racoon")


class DebianIPSec(IPSec, DebianPlugin, UbuntuPlugin):

    files = ('/etc/ipsec-tools.conf',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ipsec-tools.conf",
            "/etc/ipsec-tools.d",
            "/etc/default/setkey"
        ])

# vim: set et ts=4 sw=4 :
