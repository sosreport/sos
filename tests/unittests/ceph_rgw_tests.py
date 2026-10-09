# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json
import os
import re
import shutil
import tempfile
import unittest

from sos.policies.distros import LinuxPolicy
from sos.policies.init_systems import InitSystem
from sos.report.plugins.ceph_rgw import CephRGW


class MockOptions:
    all_logs = False
    dry_run = False
    since = None
    log_size = 25
    allow_system_changes = False
    no_postproc = False
    skip_files = []
    skip_commands = []
    sysroot = None


def make_plugin(sysroot):
    """Build a CephRGW instance rooted at a throwaway sysroot."""
    return CephRGW({
        'sysroot': sysroot,
        'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
        'cmdlineopts': MockOptions(),
        'devices': {}
    })


def write_daemon(sysroot, reldir, entity=None):
    """Create a fake RGW daemon directory, optionally with a keyring.

    :param reldir:  Daemon directory, relative to the sysroot
    :param entity:  CephX entity to write a ``[client.<entity>]`` header for,
                    or None to create the directory without a keyring
    """
    ddir = os.path.join(sysroot, reldir.lstrip(os.sep))
    os.makedirs(ddir, exist_ok=True)
    if entity is not None:
        with open(os.path.join(ddir, 'keyring'), 'w',
                  encoding='utf-8') as kfile:
            kfile.write(f"[client.{entity}]\n\tkey = PUMPUPTHEJAM==\n")
    return ddir


class CephRGWDaemonDiscoveryTests(unittest.TestCase):
    """The identity must come from the deployed daemon, never the hostname."""

    def setUp(self):
        self.sysroot = tempfile.mkdtemp()
        self.plugin = make_plugin(self.sysroot)

    def tearDown(self):
        shutil.rmtree(self.sysroot)

    def test_no_daemons_deployed(self):
        self.assertEqual([], self.plugin._get_rgw_daemons())

    def test_entity_read_from_keyring(self):
        entity = 'rgw.sostest.node1.xspqmz'
        write_daemon(self.sysroot, f'/var/lib/ceph/{"a" * 8}/rgw.sostest',
                     entity=entity)
        daemons = self.plugin._get_rgw_daemons()
        self.assertEqual(1, len(daemons))
        self.assertEqual(entity, daemons[0][0])

    def test_keyring_entity_wins_over_directory_name(self):
        # cephadm names the directory rgw.<service> but the keyring holds the
        # full daemon name; the latter is what CephX will accept
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest',
                     entity='rgw.sostest.node1.xspqmz')
        name, _ = self.plugin._get_rgw_daemons()[0]
        self.assertEqual('rgw.sostest.node1.xspqmz', name)

    def test_directory_name_used_when_keyring_has_no_header(self):
        ddir = write_daemon(self.sysroot,
                            '/var/lib/ceph/fsid/rgw.sostest.node1.xspqmz')
        with open(os.path.join(ddir, 'keyring'), 'w',
                  encoding='utf-8') as kfile:
            kfile.write("this file has no client section\n")
        name, _ = self.plugin._get_rgw_daemons()[0]
        self.assertEqual('rgw.sostest.node1.xspqmz', name)

    def test_packaged_layout_strips_cluster_prefix(self):
        ddir = write_daemon(self.sysroot, '/var/lib/ceph/radosgw/ceph-rgw.n1')
        with open(os.path.join(ddir, 'keyring'), 'w',
                  encoding='utf-8') as kfile:
            kfile.write("no header here\n")
        name, _ = self.plugin._get_rgw_daemons()[0]
        self.assertEqual('rgw.n1', name)

    def test_directory_without_keyring_is_skipped(self):
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest')
        self.assertEqual([], self.plugin._get_rgw_daemons())

    def test_hostname_is_never_used_as_identity(self):
        # The regression this plugin previously shipped: an identity of
        # 'rgw.' + gethostname(), which matches no keyring under cephadm
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest',
                     entity='rgw.sostest.node1.xspqmz')
        names = [n for n, _ in self.plugin._get_rgw_daemons()]
        self.assertNotIn(f'rgw.{os.uname().nodename}', names)

    def test_both_layouts_discovered_together(self):
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.cephadm',
                     entity='rgw.cephadm.node1.xspqmz')
        write_daemon(self.sysroot, '/var/lib/ceph/radosgw/ceph-rgw.node1',
                     entity='rgw.node1')
        names = sorted(n for n, _ in self.plugin._get_rgw_daemons())
        self.assertEqual(['rgw.cephadm.node1.xspqmz', 'rgw.node1'], names)

    def test_unreadable_keyring_does_not_raise(self):
        missing = os.path.join(self.sysroot, 'nope', 'keyring')
        self.assertIsNone(self.plugin._get_keyring_entity(missing))


class CephRGWAuthCandidateTests(unittest.TestCase):
    """Candidates must be ordered most- to least-capable."""

    def setUp(self):
        self.sysroot = tempfile.mkdtemp()
        self.plugin = make_plugin(self.sysroot)
        self.plugin.get_all_containers_by_regex = lambda regex: []

    def tearDown(self):
        shutil.rmtree(self.sysroot)

    def _with_container(self, name='ceph-fsid-rgw-sostest-node1-xspqmz'):
        self.plugin.get_all_containers_by_regex = \
            lambda regex: [('cid0', name)]
        return name

    def test_microceph_keeps_its_single_identity(self):
        self.assertEqual([(None, ['--id', 'radosgw.gateway'])],
                         self.plugin._get_auth_candidates(True))

    def test_host_default_identity_tried_first(self):
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest',
                     entity='rgw.sostest.node1.xspqmz')
        self.assertEqual((None, []),
                         self.plugin._get_auth_candidates(False)[0])

    def test_container_candidate_names_keyring_explicitly(self):
        # cephadm bind-mounts the daemon dir somewhere CephX does not search,
        # so an --id alone is not enough inside the container
        cname = self._with_container()
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest',
                     entity='rgw.sostest.node1.xspqmz')
        candidates = self.plugin._get_auth_candidates(False)
        self.assertIn(
            (cname, ['--id', 'rgw.sostest.node1.xspqmz', '--keyring',
                     '/var/lib/ceph/radosgw/ceph-rgw.sostest.node1.xspqmz'
                     '/keyring']),
            candidates)

    def test_container_candidates_precede_host_keyring(self):
        cname = self._with_container()
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest',
                     entity='rgw.sostest.node1.xspqmz')
        containers = [c for c, _ in self.plugin._get_auth_candidates(False)]
        self.assertLess(containers.index(cname),
                        len(containers) - 1 - containers[::-1].index(None))

    def test_host_keyring_candidate_is_offered(self):
        write_daemon(self.sysroot, '/var/lib/ceph/fsid/rgw.sostest',
                     entity='rgw.sostest.node1.xspqmz')
        keyring = os.path.join(self.sysroot, 'var/lib/ceph/fsid',
                               'rgw.sostest', 'keyring')
        self.assertIn(
            (None, ['--id', 'rgw.sostest.node1.xspqmz', '--keyring', keyring]),
            self.plugin._get_auth_candidates(False))

    def test_container_without_daemon_dir_still_offered(self):
        cname = self._with_container()
        self.assertIn((cname, []),
                      self.plugin._get_auth_candidates(False))


class CephRGWAuthResolutionTests(unittest.TestCase):
    """Probing stops at the first identity the cluster actually accepts."""

    ZONES = '{"zones": ["default"]}'

    def setUp(self):
        self.sysroot = tempfile.mkdtemp()
        self.plugin = make_plugin(self.sysroot)
        self.attempts = []

    def tearDown(self):
        shutil.rmtree(self.sysroot)

    # distinct from None, which is itself a valid container value meaning
    # "run on the host"
    NEVER = object()

    def _stub(self, candidates, succeed_on=NEVER):
        self.plugin._get_auth_candidates = lambda microceph: candidates

        # pylint: disable=unused-argument
        def fake_exec(cmd, container=None, **kwargs):
            self.attempts.append((container, cmd))
            if succeed_on is not self.NEVER and container == succeed_on:
                return {'status': 0, 'output': self.ZONES}
            return {'status': 1, 'output': 'unable to find a keyring'}

        self.plugin.exec_cmd = fake_exec

    def test_first_working_identity_is_used(self):
        self._stub([(None, []), ('rgwcon', ['--id', 'x'])],
                   succeed_on=None)
        container, args, zones = self.plugin._resolve_rgw_auth(False)
        self.assertIsNone(container)
        self.assertEqual([], args)
        self.assertEqual(self.ZONES, zones)
        self.assertEqual(1, len(self.attempts))

    def test_failing_candidates_are_skipped(self):
        self._stub([(None, []), ('rgwcon', ['--id', 'x'])],
                   succeed_on='rgwcon')
        container, args, _ = self.plugin._resolve_rgw_auth(False)
        self.assertEqual('rgwcon', container)
        self.assertEqual(['--id', 'x'], args)
        self.assertEqual(2, len(self.attempts))

    def test_all_candidates_failing_returns_none(self):
        self._stub([(None, []), ('rgwcon', ['--id', 'x'])])
        self.assertEqual((None, None, None),
                         self.plugin._resolve_rgw_auth(False))

    def test_probe_uses_zone_list(self):
        self._stub([(None, [])], succeed_on=None)
        self.plugin._resolve_rgw_auth(False)
        self.assertEqual('radosgw-admin zone list', self.attempts[0][1])


class CephRGWZoneDetailTests(unittest.TestCase):
    """Zone and zonegroup definitions must be collected, and kept distinct."""

    def setUp(self):
        self.sysroot = tempfile.mkdtemp()
        self.plugin = make_plugin(self.sysroot)
        self.collected = []
        self.plugin.add_cmd_output = self._record

    def tearDown(self):
        shutil.rmtree(self.sysroot)

    # pylint: disable=unused-argument
    def _record(self, cmds, container=None, suggest_filename=None, **kwargs):
        self.collected.append((cmds, container, suggest_filename))

    def _stub_zonegroups(self, payload, status=0):
        self.plugin.exec_cmd = \
            lambda cmd, container=None, **kw: {'status': status,
                                               'output': payload}

    def test_zonegroup_get_used_for_zonegroups(self):
        # this previously ran 'zone get --rgw-zonegroup=', so zonegroup
        # definitions were never actually collected
        self._stub_zonegroups('{"zonegroups": ["default"]}')
        self.plugin._add_zone_details('radosgw-admin', None,
                                      '{"zones": []}')
        cmds = [c for c, _, _ in self.collected]
        self.assertIn('radosgw-admin zonegroup get --rgw-zonegroup=default',
                      cmds)

    def test_zone_get_used_for_zones(self):
        self._stub_zonegroups('{"zonegroups": []}')
        self.plugin._add_zone_details('radosgw-admin', None,
                                      '{"zones": ["default"]}')
        cmds = [c for c, _, _ in self.collected]
        self.assertIn('radosgw-admin zone get --rgw-zone=default', cmds)

    def test_per_zone_filenames_are_distinct(self):
        # the resolved identity and keyring push these past NAME_MAX, and
        # _mangle_command() truncates rather than hashing, so without an
        # explicit filename every zone would land on the same file
        self._stub_zonegroups('{"zonegroups": []}')
        self.plugin._add_zone_details(
            'radosgw-admin --id rgw.sostest.node1.xspqmz --keyring '
            '/var/lib/ceph/radosgw/ceph-rgw.sostest.node1.xspqmz/keyring',
            None, '{"zones": ["east", "west", "default"]}')
        names = [n for _, _, n in self.collected]
        self.assertEqual(3, len(names))
        self.assertEqual(len(names), len(set(names)))
        self.assertIn('radosgw-admin_zone_get_east', names)

    def test_container_is_propagated(self):
        self._stub_zonegroups('{"zonegroups": []}')
        self.plugin._add_zone_details('radosgw-admin', 'rgwcon',
                                      '{"zones": ["default"]}')
        self.assertEqual(['rgwcon'], [c for _, c, _ in self.collected])

    def test_malformed_zone_list_does_not_raise(self):
        self._stub_zonegroups('{"zonegroups": []}')
        self.plugin._add_zone_details('radosgw-admin', None, 'not json')
        self.assertEqual([], self.collected)

    def test_zone_list_without_expected_key_does_not_raise(self):
        self._stub_zonegroups('{"zonegroups": []}')
        self.plugin._add_zone_details('radosgw-admin', None, '{"other": 1}')
        self.assertEqual([], self.collected)

    def test_failed_zonegroup_list_is_tolerated(self):
        self._stub_zonegroups('', status=1)
        self.plugin._add_zone_details('radosgw-admin', None,
                                      '{"zones": ["default"]}')
        cmds = [c for c, _, _ in self.collected]
        self.assertEqual(['radosgw-admin zone get --rgw-zone=default'], cmds)


class CephRGWSetupTests(unittest.TestCase):
    """Nothing is collected until an identity has been proven to work."""

    def setUp(self):
        self.sysroot = tempfile.mkdtemp()
        self.plugin = make_plugin(self.sysroot)
        self.collected = []
        self.plugin.add_copy_spec = lambda *a, **kw: None
        self.plugin.add_forbidden_path = lambda *a, **kw: None
        self.plugin.add_cmd_output = self._record

    def tearDown(self):
        shutil.rmtree(self.sysroot)

    # pylint: disable=unused-argument
    def _record(self, cmds, container=None, suggest_filename=None, **kwargs):
        self.collected.append((cmds, container, suggest_filename))

    def test_no_commands_collected_without_credentials(self):
        # the reported symptom was 20 files each holding the same auth error
        self.plugin._resolve_rgw_auth = lambda microceph: (None, None, None)
        self.plugin.setup()
        self.assertEqual([], self.collected)

    def test_commands_collected_once_auth_resolves(self):
        self.plugin._resolve_rgw_auth = \
            lambda microceph: (None, [], '{"zones": []}')
        self.plugin._add_zone_details = lambda *a, **kw: None
        self.plugin.setup()
        self.assertTrue(self.collected)
        cmds = [c for c, _, _ in self.collected]
        self.assertIn('radosgw-admin sync status', cmds)

    def test_resolved_identity_is_applied_to_every_command(self):
        self.plugin._resolve_rgw_auth = \
            lambda microceph: ('rgwcon', ['--id', 'rgw.a.b.c'],
                               '{"zones": []}')
        self.plugin._add_zone_details = lambda *a, **kw: None
        self.plugin.setup()
        for cmd, container, _ in self.collected:
            self.assertTrue(cmd.startswith('radosgw-admin --id rgw.a.b.c '))
            self.assertEqual('rgwcon', container)

    def test_collected_filenames_are_distinct(self):
        self.plugin._resolve_rgw_auth = \
            lambda microceph: (None, [], '{"zones": []}')
        self.plugin._add_zone_details = lambda *a, **kw: None
        self.plugin.setup()
        names = [n for _, _, n in self.collected]
        self.assertEqual(len(names), len(set(names)))


class CephRGWPostprocTests(unittest.TestCase):
    """Obfuscating the keys must not break the JSON around them."""

    SAMPLE = json.dumps({
        'name': 'default',
        'system_key': {'access_key': 'AKIAEXAMPLE',
                       'secret_key': 'c3VwZXJzZWNyZXQ='},
        'placement_pools': [],
    }, indent=4)

    def setUp(self):
        self.sysroot = tempfile.mkdtemp()
        self.plugin = make_plugin(self.sysroot)
        self.subs = []
        self.plugin.do_cmd_output_sub = \
            lambda cmd, regexp, subst: self.subs.append((cmd, regexp, subst))

    def tearDown(self):
        shutil.rmtree(self.sysroot)

    def _obfuscated(self):
        self.plugin.postproc()
        self.assertEqual(1, len(self.subs))
        _, regexp, subst = self.subs[0]
        return re.sub(regexp, subst, self.SAMPLE)

    def test_output_still_parses_as_json(self):
        # a greedy match to end-of-line also eats the trailing comma, which
        # leaves the archived zone get output unparseable
        self.assertEqual('default', json.loads(self._obfuscated())['name'])

    def test_keys_are_obfuscated(self):
        keys = json.loads(self._obfuscated())['system_key']
        self.assertEqual('**********', keys['access_key'])
        self.assertEqual('**********', keys['secret_key'])

    def test_plaintext_keys_are_gone(self):
        result = self._obfuscated()
        self.assertNotIn('AKIAEXAMPLE', result)
        self.assertNotIn('c3VwZXJzZWNyZXQ=', result)

    def test_surrounding_fields_are_untouched(self):
        self.assertIn('placement_pools', json.loads(self._obfuscated()))


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
