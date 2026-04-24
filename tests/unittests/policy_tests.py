# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json
import logging
import unittest
from unittest.mock import patch, mock_open, MagicMock

from avocado.utils import distro

from sos.policies import Policy, import_policy
from sos.policies.distros import LinuxPolicy
from sos.policies.distros.redhat import RedHatCoreOSPolicy
from sos.policies.package_managers import PackageManager, MultiPackageManager
from sos.policies.package_managers.rpm import RpmPackageManager
from sos.policies.package_managers.dpkg import DpkgPackageManager
from sos.report.plugins import (Plugin, IndependentPlugin,
                                RedHatPlugin, DebianPlugin)


class FauxPolicy(Policy):
    distro = "Faux"

    @classmethod
    def check(cls, remote=''):
        return False


class FauxLinuxPolicy(LinuxPolicy):
    distro = "FauxLinux"

    @classmethod
    def check(cls, remote=''):
        return False

    @classmethod
    def set_forbidden_paths(cls):
        return ['/etc/secret']


class FauxPlugin(Plugin, IndependentPlugin):
    pass


class FauxRedHatPlugin(Plugin, RedHatPlugin):
    pass


class FauxDebianPlugin(Plugin, DebianPlugin):
    pass


class PolicyTests(unittest.TestCase):

    def test_independent_only(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertTrue(p.validate_plugin(FauxPlugin))

    def test_forbidden_paths_building(self):
        p = FauxLinuxPolicy(probe_runtime=False)
        self.assertTrue('*.pyc' in p.forbidden_paths)
        self.assertTrue('/etc/passwd' in p.forbidden_paths)
        self.assertTrue('/etc/secret' in p.forbidden_paths)

    def test_redhat(self):
        p = FauxPolicy()
        p.valid_subclasses = [RedHatPlugin]

        self.assertTrue(p.validate_plugin(FauxRedHatPlugin))

    def test_debian(self):
        p = FauxPolicy()
        p.valid_subclasses = [DebianPlugin]

        self.assertTrue(p.validate_plugin(FauxDebianPlugin))

    def test_fails(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertFalse(p.validate_plugin(FauxDebianPlugin))

    def test_can_import(self):
        self.assertTrue(import_policy('redhat') is not None)

    def test_cant_import(self):
        self.assertTrue(import_policy('notreal') is None)


class PackageManagerTests(unittest.TestCase):

    def setUp(self):
        self.pm = PackageManager()

    def test_default_all_pkgs(self):
        self.assertEqual(self.pm.packages, {})

    def test_default_all_pkgs_by_name(self):
        self.assertEqual(self.pm.all_pkgs_by_name('doesntmatter'), [])

    def test_default_all_pkgs_by_name_regex(self):
        self.assertEqual(
            self.pm.all_pkgs_by_name_regex('.*doesntmatter$'), [])

    def test_default_pkg_by_name(self):
        self.assertEqual(self.pm.pkg_by_name('foo'), None)


class RpmPackageManagerTests(unittest.TestCase):

    def setUp(self):
        if distro.detect().name not in ['fedora', 'centos', 'rhel']:
            self.skipTest('Not running on an RPM distribution')
        self.pm = RpmPackageManager()

    def test_load_all_packages(self):
        self.assertNotEqual(self.pm.packages, {})

    def test_pkg_is_formatted(self):
        kpkg = self.pm.pkg_by_name('grep')
        self.assertIsInstance(kpkg, dict)
        self.assertIsInstance(kpkg['version'], list)
        self.assertEqual(kpkg['pkg_manager'], 'rpm')


class DpkgPackageManagerTests(unittest.TestCase):

    def setUp(self):
        if distro.detect().name not in ['Ubuntu', 'debian']:
            self.skipTest('Not running on a dpkg distribution')
        self.pm = DpkgPackageManager()

    def test_load_all_packages(self):
        self.assertNotEqual(self.pm.packages, {})

    def test_pkg_is_formatted(self):
        kpkg = self.pm.pkg_by_name('grep')
        self.assertIsInstance(kpkg, dict)
        self.assertIsInstance(kpkg['version'], list)
        self.assertEqual(kpkg['pkg_manager'], 'dpkg')


class MultiPackageManagerTests(unittest.TestCase):

    def setUp(self):
        self.pm = MultiPackageManager(primary=RpmPackageManager,
                                      fallbacks=[DpkgPackageManager])

    def test_load_all_packages(self):
        self.assertNotEqual(self.pm.packages, {})

    def test_pkg_is_formatted(self):
        kpkg = self.pm.pkg_by_name('grep')
        self.assertIsInstance(kpkg, dict)
        self.assertIsInstance(kpkg['version'], list)
        _local = distro.detect().name
        if _local in ['Ubuntu', 'debian']:
            self.assertEqual(kpkg['pkg_manager'], 'dpkg')
        else:
            self.assertEqual(kpkg['pkg_manager'], 'rpm')


class RedHatCoreOSArchiveNameTests(unittest.TestCase):

    def _make_policy(self, hostname='master-0.mycluster.example.com'):
        policy = RedHatCoreOSPolicy.__new__(RedHatCoreOSPolicy)
        policy.hostname = hostname
        policy.sysroot = '/host'
        policy.soslog = logging.getLogger('test')
        return policy

    def _make_currentconfig(self, role):
        return json.dumps({
            'metadata': {
                'labels': {
                    'machineconfiguration.openshift.io/role': role
                }
            }
        })

    def _make_kubeconfig(self, cluster='mycluster', domain='example.com',
                         api_prefix='api-int'):
        return (
            "apiVersion: v1\n"
            "clusters:\n"
            "- cluster:\n"
            f"    server: https://{api_prefix}.{cluster}.{domain}:6443\n"
            f"  name: {cluster}\n"
        )

    # _get_node_role tests

    def test_get_node_role_master(self):
        policy = self._make_policy()
        config = self._make_currentconfig('master')
        with patch('builtins.open', mock_open(read_data=config)):
            self.assertEqual(policy._get_node_role(), 'master')

    def test_get_node_role_worker(self):
        policy = self._make_policy()
        config = self._make_currentconfig('worker')
        with patch('builtins.open', mock_open(read_data=config)):
            self.assertEqual(policy._get_node_role(), 'worker')

    def test_get_node_role_missing_file(self):
        policy = self._make_policy()
        with patch('builtins.open', side_effect=IOError):
            self.assertEqual(policy._get_node_role(), '')

    def test_get_node_role_bad_json(self):
        policy = self._make_policy()
        with patch('builtins.open', mock_open(read_data='not json')):
            self.assertEqual(policy._get_node_role(), '')

    def test_get_node_role_from_owner_reference(self):
        policy = self._make_policy()
        config = json.dumps({
            'metadata': {
                'labels': {},
                'name': 'rendered-master-abc123',
                'ownerReferences': [{
                    'kind': 'MachineConfigPool',
                    'name': 'master'
                }]
            }
        })
        with patch('builtins.open', mock_open(read_data=config)):
            self.assertEqual(policy._get_node_role(), 'master')

    def test_get_node_role_from_rendered_name(self):
        policy = self._make_policy()
        config = json.dumps({
            'metadata': {
                'name': 'rendered-worker-abc123'
            }
        })
        with patch('builtins.open', mock_open(read_data=config)):
            self.assertEqual(policy._get_node_role(), 'worker')

    def test_get_node_role_no_label_no_owner_no_name(self):
        policy = self._make_policy()
        config = json.dumps({'metadata': {}})
        with patch('builtins.open', mock_open(read_data=config)):
            self.assertEqual(policy._get_node_role(), '')

    # _get_cluster_name tests

    def test_get_cluster_name_from_kubeconfig(self):
        policy = self._make_policy('master-0.mycluster.example.com')
        kubeconfig = self._make_kubeconfig('mycluster')
        with patch('builtins.open', mock_open(read_data=kubeconfig)):
            self.assertEqual(policy._get_cluster_name(), 'mycluster')

    def test_get_cluster_name_from_kubeconfig_api_prefix(self):
        policy = self._make_policy('master-0.mycluster.example.com')
        kubeconfig = self._make_kubeconfig('mycluster', api_prefix='api')
        with patch('builtins.open', mock_open(read_data=kubeconfig)):
            self.assertEqual(policy._get_cluster_name(), 'mycluster')

    def test_get_cluster_name_kubeconfig_missing_falls_back_to_hostname(self):
        policy = self._make_policy('master-0.mycluster.example.com')
        with patch('builtins.open', side_effect=IOError):
            self.assertEqual(policy._get_cluster_name(), 'mycluster')

    def test_get_cluster_name_short_hostname(self):
        policy = self._make_policy('master-0')
        with patch('builtins.open', side_effect=IOError):
            self.assertEqual(policy._get_cluster_name(), '')

    def test_get_cluster_name_complex_fqdn(self):
        policy = self._make_policy('worker-1.prod-cluster.dc1.example.com')
        with patch('builtins.open', side_effect=IOError):
            self.assertEqual(policy._get_cluster_name(), 'prod-cluster')

    # get_archive_name tests

    def _make_policy_for_archive(
            self, hostname='master-0.mycluster.example.com',
            label='', case_id=''):
        policy = self._make_policy(hostname)
        policy.name_pattern = 'friendly'
        policy.case_id = case_id
        opts = MagicMock()
        opts.label = label
        policy.commons = {'cmdlineopts': opts}
        return policy

    def test_archive_name_includes_role_and_cluster(self):
        policy = self._make_policy_for_archive()
        with patch.object(policy, '_get_node_role', return_value='master'), \
             patch.object(policy, '_get_cluster_name',
                          return_value='mycluster'):
            name = policy.get_archive_name()
        self.assertTrue(name.startswith('sosreport-master-0-'))
        self.assertIn('master-mycluster', name)

    def test_archive_name_preserves_user_label(self):
        policy = self._make_policy_for_archive(label='debug')
        with patch.object(policy, '_get_node_role', return_value='worker'), \
             patch.object(policy, '_get_cluster_name',
                          return_value='prod'):
            name = policy.get_archive_name()
        self.assertIn('worker-prod-debug', name)

    def test_archive_name_role_only(self):
        policy = self._make_policy_for_archive()
        with patch.object(policy, '_get_node_role', return_value='master'), \
             patch.object(policy, '_get_cluster_name', return_value=''):
            name = policy.get_archive_name()
        self.assertIn('-master-', name)
        self.assertNotIn('mycluster', name)

    def test_archive_name_fallback_when_nothing_detected(self):
        policy = self._make_policy_for_archive()
        with patch.object(policy, '_get_node_role', return_value=''), \
             patch.object(policy, '_get_cluster_name', return_value=''):
            name = policy.get_archive_name()
        self.assertTrue(name.startswith('sosreport-master-0-'))
        self.assertNotIn('master-master', name)

    def test_archive_name_restores_original_label(self):
        policy = self._make_policy_for_archive(label='original')
        with patch.object(policy, '_get_node_role', return_value='master'), \
             patch.object(policy, '_get_cluster_name',
                          return_value='mycluster'):
            policy.get_archive_name()
        self.assertEqual(policy.commons['cmdlineopts'].label, 'original')


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
