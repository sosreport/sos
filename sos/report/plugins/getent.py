# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import IndependentPlugin
from sos.report.plugins import Plugin


class Getent(Plugin, IndependentPlugin):

    short_desc = 'query Name Service Switch (NSS) databases'

    plugin_name = "getent"
    profiles = ('system',)
    verify_packages = ('glibc-common', 'libc-bin', 'glibc')

    def setup(self):

        # For reference. This databases are not collected.
        # ["ahosts", "ahostsv4", "ahostsv6", "ethers", "gshadow", "hosts",
        # "networks", "passwd", "services", "shadow"]

        # Collected databases
        databases = ["aliases", "group", "netgroup", "protocols", "rpc"]

        for db in databases:
            self.add_cmd_output(f"getent {db}")

# vim: set et ts=4 sw=4 :
