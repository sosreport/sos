# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Pmem(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    '''Persistent Memory Device Plugin

    This plugin collects data from Persistent Memory Modules,
    commonly referred to as NVDIMM's or Storage Class Memory (SCM).
    '''

    plugin_name = 'pmem'
    profiles = ('storage', 'hardware', 'memory')
    # Utilities can be installed by package or self compiled
    packages = ('ndctl', 'ipmctl')
    commands = ('ndctl', 'ipmctl')

    def setup(self):
        # Copy the contents of the /etc/ndctl directory and ipmctl.conf file
        self.add_copy_spec([
            "/etc/ndctl",
            "/etc/ipmctl.conf"
        ])

        ''' Use the ndctl-list(1) command to collect:
        -i      Include idle (not enabled) devices in the listing
        -vvv    Increase verbosity of the output
        -B      Include bus info in the listing
        -D      Include dimm info in the listing
        -F      Include dimm firmware info in the listing
        -H      Include dimm health info in the listing
        -M      Include media errors (badblocks) in the listing
        -N      Include namespace info in the listing
        -R      Include region info in the listing
        -X      Include device-dax info in the listing

        Output is JSON formatted
        '''
        self.add_cmd_output([
            "ndctl --version",
            "ndctl list -vvv",
            "ndctl list -iBDFHMNRX",
            "ndctl read-labels -j all"
        ])

        ''' Use the Intel ipmctl(1) to collect data from
        Intel(R) Optane(TM) DC Persistent Memory Modules.
        ixpdimm-cli is now deprecated and removed from this module.
        '''
        self.add_cmd_output([
            "ipmctl version",
            "ipmctl show -cap",
            "ipmctl show -dimm",
            "ipmctl show -a -dimm",
            "ipmctl show -dimm -pcd",
            "ipmctl show -dimm -performance",
            "ipmctl show -error Thermal -dimm",
            "ipmctl show -error Media -dimm",
            "ipmctl show -event",
            "ipmctl show -firmware",
            "ipmctl show -memoryresources",
            "ipmctl show -preferences",
            "ipmctl show -region",
            "ipmctl show -sensor",
            "ipmctl show -socket",
            "ipmctl show -system",
            "ipmctl show -system -capabilities",
            "ipmctl show -system -host",
            "ipmctl show -topology"
        ])

# vim: set et ts=4 sw=4 :
