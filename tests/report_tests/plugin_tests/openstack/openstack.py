# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json

from sos_tests import StageTwoReportTest, ubuntu_only
from sos.utilities import shell_out

from avocado.utils import distro
from avocado.utils.software_manager import distro_packages


class OpenstackConfScrubbedTest(StageTwoReportTest):
    """Ensure that the various openstack confs are picked up and properly
    scrubbed

    :avocado: tags=stagetwo
    """

    sos_cmd = ('-o openstack_cinder,openstack_keystone,openstack_glance,'
               'openstack_heat,openstack_neutron,openstack_nova')
    files = [
        ('cinder.conf', '/etc/cinder/cinder.conf'),
        ('keystone.domain1.conf',
         '/etc/keystone/domains/keystone.domain1.conf'),
        ('keystone.conf', '/etc/keystone/keystone.conf'),
        ('glance-api.conf', '/etc/glance/glance-api.conf'),
        ('heat.conf', '/etc/heat/heat.conf'),
        ('neutron.conf', '/etc/neutron/neutron.conf'),
        ('nova.conf', '/etc/nova/nova.conf'),
        ('heat.conf', '/etc/heat/heat.conf'),
    ]

    packages = {
        'rhel': ['openstack-cinder', 'openstack-glance',
                 'openstack-heat-common', 'openstack-keystone',
                 'openstack-nova'],
        'Ubuntu': ['cinder-common', 'glance-common', 'heat-common',
                   'keystone-common', 'nova-common']
    }

    openstack_only = True

    def setup_mocked_packages(self):
        this_distro = distro.detect()
        if this_distro.name == "centos" or this_distro.name == "centos-stream":
            shell_out("dnf config-manager --enable crb")
            shell_out("dnf config-manager --enable powertools")
            pkg_to_install = "centos-release-openstack-yoga"
            installed = distro_packages.install_distro_packages(
                {this_distro.name: [pkg_to_install]})
            if not installed:
                raise Exception(
                    "Unable to install requested packages "
                    f"{pkg_to_install}")
            self._write_file_to_tmpdir(
                'mocked_osp_package', f'["{pkg_to_install}"]')
        super().setup_mocked_packages()

    def teardown_mocked_packages(self):
        this_distro = distro.detect()
        if this_distro.name == "centos" or this_distro.name == "centos-stream":
            pkgs = self.read_file_from_tmpdir('mocked_osp_package')
            if not pkgs:
                return
            pkgs = json.loads(pkgs)
            for pkg in pkgs:
                self.sm.remove(pkg)
        super().teardown_mocked_packages()

    def test_cinder_conf_collected_and_scrubbed(self):
        self.assertFileCollected('/etc/cinder/cinder.conf')

        values_to_mask = [
            'cmB4zBYq3VWFMNqNKFLcqS5Zq8ystLLsTd5BFLbCtX67qShnhgHFxxRFjkhbY54x',
            'wPhFqY69x94YVJc7STrVH3CfsFrrcZPYw8NS2pjhzqyzw7wrL2VnTmN58c5XTnfV',
            'Ck3r7zf6B6PscfjWhhj2zJdy8SNXYd59',
        ]
        for value in values_to_mask:
            self.assertFileNotHasContent('/etc/cinder/cinder.conf', value)

    def test_glance_conf_collected_and_scrubbed(self):
        self.assertFileCollected('/etc/glance/glance-api.conf')

        values_to_mask = [
            '4LzVZZLsPTrKw7c49ZdxqmJ8mkcWkSSnPJzgYyZWPMkrVzyB62CyCzzKVRnBS4Mz',
            'cbVtRMqPznc4M7XKVG73yPn5fBX4NXYSC4bMb7PGYTL5RkWXnc8ZsZ9hrJy2hynf',
            'rM5hSHsw8JSV2mJVkcszMBxtVsHbG4MW',
        ]

        for value in values_to_mask:
            self.assertFileNotHasContent('/etc/glance/glance-api.conf', value)

    def test_heat_conf_collected_and_scrubbed(self):
        self.assertFileCollected('/etc/heat/heat.conf')

        values_to_mask = [
            'TH4BRqtVNt4WhWkrqmKZX4Kpf4pr7cCT',
            'sXNkqpmgprNs69SdF7jXM9JP9Nfc7m7n',
            'zy5sPgTkbwF6qL6Gc4wngyxYFwB3r77HjRJtXWbVP4Cf4psmfJmqw2MZqZ8jxxFC',
            'Jbf8JkTW2PXYC6hH5YC8XzmjYrLkcT6wJSZzccstNcnnFNNsKXz54PVd7NhKT45j',
        ]

        for value in values_to_mask:
            self.assertFileNotHasContent('/etc/heat/heat.conf', value)

    def test_keystone_conf_collected_and_scrubbed(self):
        self.assertFileCollected('/etc/keystone/keystone.conf')
        self.assertFileCollected('/etc/keystone/keystone.policy.yaml')

        self.assertFileNotHasContent(
            '/etc/keystone/keystone.conf', '2zx9jZZtxdn4grG3xcMV4PwgGwY7X7fP')

    def test_keystone_ldap_conf_scrubbed(self):
        self.assertFileNotHasContent(
            '/etc/keystone/domains/keystone.domain1.conf', 'crapper')

    @ubuntu_only
    def test_neutron_ml2_certs_not_collected(self):
        self.assertFileNotCollected('/etc/neutron/plugins/ml2/cert_host')
        self.assertFileNotCollected('/etc/neutron/plugins/ml2/key_host')
        self.assertFileNotCollected(
            '/etc/neutron/plugins/ml2/neutron-api-plugin-ovn.crt')

    def test_neutron_conf_collected_and_scrubbed(self):
        self.assertFileCollected('/etc/neutron/neutron.conf')
        self.assertFileCollected('/etc/neutron/plugins/ml2/ml2_conf.ini')

        values_to_mask = [
            'KwGKnxV4tSVMpyhyz8Pj8gXnncrfyKr7nYFJhN7t8m6V3jL8jHKqLchgc6fjLMJ6',
            '2VX9YzhHm7gMsr7RFLx8Ypckpq5fCshsNM8CfMYBXWZcCPKcwcjXb9rFtzWcBgM4',
            '8ZMkYGjw5bsYwc6cx72b9ZVBrCKM5JMB',
        ]

        for value in values_to_mask:
            self.assertFileNotHasContent('/etc/neutron/neutron.conf', value)

    def test_nova_conf_collected_and_scrubbed(self):
        self.assertFileCollected('/etc/nova/nova.conf')

        values_to_mask = [
            'JpdsBfXHTwFMmTHsP8WY2gTRpb4ZrLfN6VmT2666TtZfjYcGKMnrJd7pPRxqtNfs',
            'WCBG8sqmmpKPYBbpVNSjfsScpmh55W2jJgPnXYb7zM2Rr469g2LL4x642R67dFyX',
            'Vrn7SkRMHL8FzjNg2NJjwF57t7hJfhjj',
        ]

        for value in values_to_mask:
            self.assertFileNotHasContent('/etc/nova/nova.conf', value)

# vim: set et ts=4 sw=4 :
