# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class VMWare(Plugin, RedHatPlugin):

    short_desc = 'VMWare client information'

    plugin_name = 'vmware'
    profiles = ('virt',)
    packages = ('open-vm-tools', 'VMWare-Tools')
    files = ('/etc/vmware-tools', '/etc/vmware')
    commands = ('vmware-toolbox-cmd',)
    services = ('vmtoolsd',)

    def setup(self):
        self.add_copy_spec([
            "/etc/vmware-tools/",
            "/etc/vmware/locations",
            "/etc/vmware/config",
            "/proc/vmmemctl",
            "/sys/kernel/debug/vmmemctl",
            "/var/log/vmware-network.log",
            "/var/log/vmware-vgauthsvc.log.0",
            "/var/log/vmware-vmsvc-root.log",
            "/var/log/vmware-vmtoolsd-root.log",
            "/var/log/vmware-vmusr-root.log"
        ])

        self.add_cmd_output([
            "vmware-checkvm",
            "vmware-toolbox-cmd device list",
            "vmware-toolbox-cmd -v",
            "vmware-toolbox-cmd timesync status"
        ])

        stats = self.exec_cmd("vmware-toolbox-cmd stat raw")
        if stats['status'] == 0:
            for _stat in stats['output'].splitlines():
                self.add_cmd_output("vmware-toolbox-cmd stat raw text %s"
                                    % _stat)

# vim: set et ts=4 sw=4 :
