# Copyright (C) 2016 Jorge Niedbalski <niedbalski@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin, SoSPredicate


class LXD(Plugin, UbuntuPlugin):

    short_desc = 'LXD container hypervisor'
    plugin_name = 'lxd'
    profiles = ('container',)
    packages = ('lxd',)
    commands = ('lxc', 'lxd',)

    def setup(self):

        lxd_kmods = [
            'bpfilter',
            'ebtable_filter',
            'ebtables',
            'ip6table_filter',
            'ip6table_mangle',
            'ip6table_nat',
            'ip6table_raw',
            'ip6_tables',
            'iptable_filter',
            'iptable_mangle',
            'iptable_nat',
            'iptable_raw',
            'nf_nat',
            'nf_tables',
        ]

        lxd_pred = SoSPredicate(self, kmods=lxd_kmods,
                                required={'kmods': 'all'})

        lxd_pkg = self.policy.package_manager.pkg_by_name('lxd')
        if lxd_pkg and lxd_pkg['pkg_manager'] == 'snap':
            self.add_cmd_output("lxd.buginfo", pred=lxd_pred)

            self.add_copy_spec([
                '/var/snap/lxd/common/config',
                '/var/snap/lxd/common/global-conf',
                '/var/snap/lxd/common/lxc/local.conf',
                '/var/snap/lxd/common/lxd/logs/*/*.conf',
            ])

            if not self.get_option("all_logs"):
                self.add_copy_spec([
                    '/var/snap/lxd/common/lxd/logs/*.log',
                    '/var/snap/lxd/common/lxd/logs/*/*.log',
                ])
            else:
                self.add_copy_spec([
                    '/var/snap/lxd/common/lxd/logs/**',
                ])
        else:
            self.add_copy_spec([
                "/etc/default/lxd-bridge",
                "/var/log/lxd/*"
            ])

            self.add_cmd_output([
                "lxc image list",
                "lxc list",
                "lxc network list",
                "lxc profile list",
                "lxc storage list"
            ], pred=lxd_pred)

            self.add_cmd_output([
                "find /var/lib/lxd -maxdepth 2 -type d -ls",
            ], suggest_filename='var-lxd-dirs.txt')

# vim: set et ts=4 sw=4 :
