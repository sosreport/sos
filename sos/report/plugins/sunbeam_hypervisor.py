# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class SunbeamHypervisor(Plugin, UbuntuPlugin):

    short_desc = "Sunbeam Hypervisor"

    plugin_name = "sunbeam_hypervisor"
    profiles = ('cloud',)
    packages = ('openstack-hypervisor',)

    plugin_timeout = 600

    services = (
        'snap.openstack-hypervisor.ceilometer-compute-agent',
        'snap.openstack-hypervisor.libvirt-exporter',
        'snap.openstack-hypervisor.libvirtd',
        'snap.openstack-hypervisor.masakari-instancemonitor',
        'snap.openstack-hypervisor.neutron-ovn-metadata-agent',
        'snap.openstack-hypervisor.nova-api-metadata',
        'snap.openstack-hypervisor.nova-compute',
        'snap.openstack-hypervisor.ovn-controller',
        'snap.openstack-hypervisor.ovs-exporter',
        'snap.openstack-hypervisor.ovs-vswitchd',
        'snap.openstack-hypervisor.ovsdb-server',
        'snap.openstack-hypervisor.virtlogd',
    )

    common_dir = '/var/snap/openstack-hypervisor/common'

    def setup(self):

        self.add_copy_spec([
            f'{self.common_dir}/*.log',
            f'{self.common_dir}/log/**/*.log',
            f'{self.common_dir}/etc',
            f'{self.common_dir}/lib/nova/instances/*/console.log',
            f'{self.common_dir}/cache/libvirt/qemu/capabilities/*.xml',
        ])

        self.add_forbidden_path([
            f'{self.common_dir}/etc/ssl/',
            f'{self.common_dir}/etc/libvirt/secrets',
            f'{self.common_dir}/etc/libvirt/passwd.db',
            f'{self.common_dir}/etc/libvirt/krb5.tab',
            f'{self.common_dir}/var/log/ovn/',
            f'{self.common_dir}/etc/pki/',
        ])

    def postproc(self):

        # libvirt confs
        match_exp = r"(\s*passwd=\s*')([^']*)('.*)"
        libvirt_path_exps = [
            fr"{self.common_dir}/etc/libvirt/qemu/.*\.xml",
            fr"{self.common_dir}/etc/libvirt/.*\.conf"
        ]
        for path_exp in libvirt_path_exps:
            self.do_path_regex_sub(path_exp, match_exp, r"\1******\3")

        # nova/neutron bits
        protect_keys = [
            ".*_key",
            ".*_pass(wd|word)?",
            "metadata_proxy_shared_secret",
            "password",
            "rbd_secret_uuid",
            "server_auth",
            "serverauth",
            "transport_url",
        ]
        connection_keys = ["connection", "sql_connection"]

        openstack_folders = [
            "nova",
            "neutron",
            "ceilometer",
            "masakarimonitors",
        ]

        self.do_path_regex_sub(
            fr'{self.common_dir}/etc/({"|".join(openstack_folders)})/*',
            fr'(^\s*({"|".join(protect_keys)})\s*=\s*)(.*)',
            r"\1*********"
        )
        self.do_path_regex_sub(
            fr'{self.common_dir}/etc/({"|".join(openstack_folders)})/*',
            fr'(^\s*({"|".join(connection_keys)})\s*=\s*(.*)'
            r'://(\w*):)(.*)(@(.*))',
            r"\1*********\6"
        )

        # hooks.log
        protect_hook_keys = [
            "password",
            "ovn_metadata_proxy_shared_secret",
            "cacert",
            "cert",
            "key",
            "ovn_cacert",
            "ovn_cert",
            "ovn_key",
            "url",
        ]

        self.do_file_sub(
            f'{self.common_dir}/hooks.log',
            fr'(\'({"|".join(protect_hook_keys)})\'):\s?\'(.+?)\'',
            r"\1: **********"
        )

# vim: et ts=4 sw=4
