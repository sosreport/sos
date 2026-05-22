# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest


class SunbeamBasicTest(StageOneReportTest):
    """Ensure that a basic execution runs as expected with simple deployment.

    :avocado: tags=sunbeam
    """

    sos_cmd = '-v -k sunbeam.juju-allow-login=True'
    arch = ['x86_64']

    ubuntu_only = True
    sos_timeout = 1200

    sunbeam_common = "/var/snap/openstack/common"
    sunbeam_current = "/var/snap/openstack/current"

    hypervisor_common = "/var/snap/openstack-hypervisor/common"

    check_obfuscate = [
        r"transport_url = \*\*\*\*\*\*\*\*\*",
        r"password = \*\*\*\*\*\*\*\*\*",
    ]

    def test_plugins_ran(self):
        self.assertPluginIncluded([
            'juju',
            'libvirt',
            'kubernetes',
            'ovn_host',
            'sunbeam',
            'sunbeam_hypervisor',
        ])

    def test_sunbeam_keys_skipped(self):
        self.assertFileGlobNotInArchive(
            f"{self.hypervisor_common}/etc/pki/**/*.pem")
        self.assertFileGlobNotInArchive(
            f"{self.hypervisor_common}/etc/ssl/**/*.pem")

    def test_sunbeam_installer_dirs_collected(self):
        self.assertFileGlobInArchive("/etc/sunbeam-installer/*")
        self.assertFileGlobInArchive("/var/log/sunbeam-installer/*")

    def test_sunbeam_openstack_config_files_collected(self):
        files_collected = [
            f'{self.sunbeam_common}/state/daemon.yaml',
            f'{self.sunbeam_common}/state/database/info.yaml',
            f'{self.sunbeam_common}/state/database/cluster.yaml',
            f'{self.sunbeam_current}/config.yaml',
        ]
        for file in files_collected:
            self.assertFileCollected(file)

    def test_sunbeam_nova_log_collected(self):
        self.assertFileCollected(
            f'{self.hypervisor_common}/var/log/nova/nova.log')

    def test_sunbeam_neutron_log_collected(self):
        self.assertFileCollected(
            f'{self.hypervisor_common}/var/log/neutron/neutron.log')

    def test_sunbeam_ovn_controller_log_collected(self):
        self.assertFileCollected(
            f'{self.hypervisor_common}/var/log/ovn/ovn-controller.log')

    def test_sunbeam_openvswitch_log_collected(self):
        self.assertFileCollected(
            f'{self.hypervisor_common}/var/log/openvswitch/ovs-vswitchd.log')
        self.assertFileCollected(
            f'{self.hypervisor_common}/var/log/openvswitch/ovsdb-server.log')

    def test_sunbeam_cluster_list_collected_(self):
        self.assertFileCollected('sos_commands/sunbeam/sunbeam_cluster_list')

    def test_sunbeam_manifest_list_collected_(self):
        self.assertFileCollected('sos_commands/sunbeam/sunbeam_manifest_list')

    def test_sunbeam_juju_configs_controller_collected(self):
        files_collected = [
            'juju_status_-m_sunbeam-controller_admin.controller',
            'juju_model-config_-m_sunbeam-controller_admin.controller',
        ]

        for file in files_collected:
            self.assertFileCollected(f'sos_commands/sunbeam/{file}')

    def test_sunbeam_nova_conf_collected_and_obfuscated(self):
        nova_conf = f'{self.hypervisor_common}/etc/nova/nova.conf'
        self.assertFileCollected(nova_conf)

        for check in self.check_obfuscate:
            self.assertFileHasContent(nova_conf, check)

    def test_sunbeam_neutron_conf_collected_and_obfuscated(self):
        neutron_conf = f'{self.hypervisor_common}/etc/neutron/neutron.conf'
        self.assertFileCollected(neutron_conf)

        for check in self.check_obfuscate:
            self.assertFileHasContent(neutron_conf, check)

    def test_sunbeam_ceilometer_conf_collected_and_obfuscated(self):
        ceilometer_conf = (f'{self.hypervisor_common}/etc/ceilometer/'
                           'ceilometer.conf')
        self.assertFileCollected(ceilometer_conf)

        for check in self.check_obfuscate:
            self.assertFileHasContent(ceilometer_conf, check)

    def test_sunbeam_masakarimonitors_conf_collected_and_obfuscated(self):
        masakari_conf = (f'{self.hypervisor_common}/etc/masakarimonitors/'
                         'masakarimonitors.conf')
        self.assertFileCollected(masakari_conf)

        self.assertFileHasContent(
            masakari_conf, r"password = \*\*\*\*\*\*\*\*\*")

# vim: et ts=4 sw=4
