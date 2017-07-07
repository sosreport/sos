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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class Nvme(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Collect config and system information about NVMe devices"""

    plugin_name = "nvme"
    packages = ('nvme-cli',)

    def get_nvme_devices(self):
        sys_block = os.listdir('/sys/block/')
        return [dev for dev in sys_block if dev.startswith('nvme')]

    def setup(self):
        for dev in self.get_nvme_devices():
            # runs nvme-cli commands
            self.add_cmd_output([
                                "nvme list",
                                "nvme list-ns /dev/%s" % dev,
                                "nvme fw-log /dev/%s" % dev,
                                "nvme list-ctrl /dev/%s" % dev,
                                "nvme id-ctrl -H /dev/%s" % dev,
                                "nvme id-ns -H /dev/%s" % dev,
                                "nvme smart-log /dev/%s" % dev,
                                "nvme error-log /dev/%s" % dev,
                                "nvme show-regs /dev/%s" % dev])

# vim: set et ts=4 sw=4 :
