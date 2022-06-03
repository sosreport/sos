# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin
import glob


class Libvirt(Plugin, IndependentPlugin):

    short_desc = 'libvirt virtualization API'

    plugin_name = 'libvirt'
    profiles = ('system', 'virt')

    def setup(self):
        libvirt_keytab = "/etc/libvirt/krb5.tab"

        # authentication databases used for libvirt SASL authentication
        self.add_forbidden_path([
            "/etc/libvirt/passwd.db",
            "/etc/libvirt/krb5.tab",
            "/var/lib/libvirt/qemu/*/master-key.aes",
            "/etc/libvirt/secrets"
        ])

        self.add_copy_spec([
            "/etc/libvirt/libvirt.conf",
            "/etc/libvirt/libvirtd.conf",
            "/etc/libvirt/lxc.conf",
            "/etc/libvirt/nwfilter/*.xml",
            "/etc/libvirt/qemu/*.xml",
            "/etc/libvirt/qemu.conf",
            "/run/libvirt/",
            "/etc/libvirt/qemu/networks/*.xml",
            "/etc/libvirt/qemu/networks/autostart/*.xml",
            "/etc/libvirt/storage/*.xml",
            "/etc/libvirt/storage/autostart/*.xml",
            "/etc/libvirt/qemu-lockd.conf",
            "/etc/libvirt/virtlockd.conf",
            "/var/lib/libvirt/dnsmasq/*",
        ])

        if not self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/libvirt/libvirtd.log",
                "/var/log/libvirt/qemu/*.log*",
                "/var/log/libvirt/lxc/*.log",
                "/var/log/libvirt/uml/*.log",
                "/var/log/swtpm/libvirt/qemu/*.log",
                "/var/log/containers/libvirt/libvirtd.log",
                "/var/log/containers/libvirt/qemu/*.log*",
                "/var/log/containers/libvirt/lxc/*.log",
                "/var/log/containers/libvirt/swtpm/libvirt/qemu/*.log",
                "/var/log/containers/libvirt/uml/*.log",
            ])
        else:
            self.add_copy_spec("/var/log/libvirt")
            self.add_copy_spec("/var/log/containers/libvirt")

        if self.path_exists(self.path_join(libvirt_keytab)):
            self.add_cmd_output("klist -ket %s" % libvirt_keytab)

        self.add_cmd_output("ls -lR /var/lib/libvirt/qemu")

        # get details of processes of KVM hosts
        for pidfile in glob.glob("/run/libvirt/*/*.pid"):
            pid = open(pidfile).read().splitlines()[0]
            for pf in ["environ", "cgroup", "maps", "numa_maps", "limits"]:
                self.add_copy_spec("/proc/%s/%s" % (pid, pf))

    def postproc(self):
        match_exp = r"(\s*passwd=\s*')([^']*)('.*)"
        libvirt_path_exps = [
            r"/etc/libvirt/qemu/.*\.xml",
            r"/run/libvirt/qemu/.*\.xml",
            r"/etc/libvirt/.*\.conf"
        ]
        for path_exp in libvirt_path_exps:
            self.do_path_regex_sub(path_exp, match_exp, r"\1******\3")

# vim: set et ts=4 sw=4 :
