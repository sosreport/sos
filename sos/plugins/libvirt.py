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


class Libvirt(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """libvirt virtualization API
    """

    plugin_name = 'libvirt'
    profiles = ('system', 'virt')

    def setup(self):
        libvirt_keytab = "/etc/libvirt/krb5.tab"

        # authentication databases used for libvirt SASL authentication
        self.add_forbidden_path("/etc/libvirt/passwd.db")
        self.add_forbidden_path("/etc/libvirt/krb5.tab")

        self.add_copy_spec([
            "/etc/libvirt/libvirt.conf",
            "/etc/libvirt/libvirtd.conf",
            "/etc/libvirt/lxc.conf",
            "/etc/libvirt/nwfilter/*.xml",
            "/etc/libvirt/qemu/*.xml",
            "/var/run/libvirt/qemu/*.xml",
            "/etc/libvirt/qemu/networks/*.xml",
            "/etc/libvirt/qemu/networks/autostart/*.xml",
            "/etc/libvirt/storage/*.xml",
            "/etc/libvirt/storage/autostart/*.xml",
            "/etc/libvirt/qemu-lockd.conf",
            "/etc/libvirt/virtlockd.conf"
        ])

        if not self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/libvirt/libvirtd.log",
                                     sizelimit=5)
            self.add_copy_spec_limit("/var/log/libvirt/qemu/*.log",
                                     sizelimit=5)
            self.add_copy_spec_limit("/var/log/libvirt/lxc/*.log", sizelimit=5)
            self.add_copy_spec_limit("/var/log/libvirt/uml/*.log", sizelimit=5)
        else:
            self.add_copy_spec("/var/log/libvirt")

        if os.path.exists(self.join_sysroot(libvirt_keytab)):
            self.add_cmd_output("klist -ket %s" % libvirt_keytab)

        self.add_cmd_output("ls -lR /var/lib/libvirt/qemu")

    def postproc(self):
        for loc in ["/etc/", "/var/run/"]:
            for xmlfile in glob.glob(loc + "libvirt/qemu/*.xml"):
                self.do_file_sub(
                    xmlfile,
                    r"(\s*passwd=\s*')([^']*)('.*)",
                    r"\1******\3"
                )

# vim: set et ts=4 sw=4 :
