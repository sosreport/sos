# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class vhostmd(Plugin, RedHatPlugin):

    short_desc = 'vhostmd virtualization metrics collection'

    plugin_name = 'vhostmd'
    profiles = ('sap', 'virt', 'system')

    packages = ('virt-what',)

    def setup(self):
        vw = self.collect_cmd_output("virt-what")['output'].splitlines()

        if not vw:
            return

        if "vmware" in vw or "kvm" in vw or "xen" in vw:
            if self.is_installed("vm-dump-metrics"):
                # if vm-dump-metrics is installed use it
                self.add_cmd_output("vm-dump-metrics",
                                    suggest_filename="virt_metrics")
            else:
                # otherwise use the raw vhostmd disk presented (256k size)
                sysblock = "/sys/block"
                if not self.path_isdir(sysblock):
                    return
                for disk in self.listdir(sysblock):
                    if "256K" in disk:
                        dev = disk.split()[0]
                        r = self.exec_cmd("dd if=/dev/%s bs=25 count=1" % dev)
                        if 'metric' in r['output']:
                            self.add_cmd_output(
                                "dd if=/dev/%s bs=256k count=1" % dev,
                                suggest_filename="virt_metrics"
                            )

# vim: et ts=4 sw=4
