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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
import glob
import os


class LibvirtClient(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """client for libvirt virtualization API
    """

    plugin_name = 'virsh'
    profiles = ('system', 'virt')

    packages = ('libvirt-client')

    def setup(self):
        # virt-manager logs
        if not self.get_option("all_logs"):
            self.add_copy_spec_limit("/root/.virt-manager/*", sizelimit=5)
        else:
            self.add_copy_spec("/root/.virt-manager/*")

        # get lit of VMs/domains
        domains_file = self.get_cmd_output_now('virsh list --all')

        # cycle through the VMs/domains list, ignore 2 header lines and latest
        # empty line, and dumpxml domain name in 2nd column
        if domains_file:
            domains_lines = open(domains_file, "r").read().splitlines()[2:]
            for domain in filter(lambda x: x, domains_lines):
                self.add_cmd_output("virsh -r dumpxml %s" % domain.split()[1],
                                    timeout=180)

# vim: et ts=4 sw=4
