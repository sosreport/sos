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
import os


class vhostmd(Plugin, RedHatPlugin):
    """vhostmd virtualization metrics collection
    """

    plugin_name = 'vhostmd'
    profiles = ['sap', 'virt', 'system']

    packages = ['virt-what']

    def setup(self):
        vw = self.get_command_output("virt-what")['output'].splitlines()

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
                if not os.path.isdir(sysblock):
                    return
                for disk in os.listdir(sysblock):
                    if "256K" in disk:
                        dev = disk.split()[0]
                        check = self.get_command_output(
                            "dd if=/dev/%s bs=25 count=1" % dev)
                        if 'metric' in check['output']:
                            self.add_cmd_output("dd if=/dev/%s bs=256k count=1"
                                                % dev,
                                                suggest_filename="virt_\
                                                        metrics")

# vim: et ts=4 sw=4
