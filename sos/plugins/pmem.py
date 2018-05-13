# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Pmem(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Persistent Memory devices
    """

    plugin_name = 'pmem'
    profiles = ('storage', 'hardware', 'memory')

    def setup(self):
        self.add_cmd_output([
            "ndctl --version",
            "ndctl list -B",
            "ndctl list -D",
            "ndctl list -iD",
            "ndctl list -iDF",
            "ndctl list -R",
            "ndctl list -iR",
            "ndctl list -M",
            "ndctl list -iM",
            "ndctl list -N",
            "ndctl list -iN",
            "ndctl list -NX",
            "ndctl list -iNX",
            "ndctl list -NRD",
            "ndctl list -iNRD",
            "ndctl list -NuRD",
            "ndctl list -iNuRD"
        ])

        self.add_cmd_output([
            "ipmctl version",
            "ipmctl show -o text -dimm",
            "ipmctl show -o text -dimm -performance",
            "ipmctl show -o text -event",
            "ipmctl show -o text -firmware",
            "ipmctl show -o text -goal",
            "ipmctl show -o text -memoryresources",
            "ipmctl show -o text -preferences",
            "ipmctl show -o text -region",
            "ipmctl show -o text -sensor",
            "ipmctl show -o text -socket",
            "ipmctl show -o text -system",
            "ipmctl show -o text -system -capabilities",
            "ipmctl show -o text -system -host",
            "ipmctl show -o text -topology"
        ])

        self.add_cmd_output([
            "ixpdimm-cli version",
            "ixpdimm-cli show -o text -dimm",
            "ixpdimm-cli show -o text -dimm -performance",
            "ixpdimm-cli show -o text -dimm",
            "ipmctl show -o text -event",
            "ipmctl show -o text -firmware",
            "ipmctl show -o text -goal",
            "ipmctl show -o text -memoryresources",
            "ipmctl show -o text -preferences",
            "ipmctl show -o text -region",
            "ipmctl show -o text -sensor",
            "ipmctl show -o text -socket",
            "ipmctl show -o text -system",
            "ipmctl show -o text -system -capabilities",
            "ipmctl show -o text -system -host",
            "ipmctl show -o text -topology"
       ])

# vim: set et ts=4 sw=4 :
