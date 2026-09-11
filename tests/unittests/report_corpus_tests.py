"""Phase 21 synthetic whole-report corpus and end-to-end assertions."""

import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.sanitizer import ReportSanitizer, ReportSanitizerError
from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.session import SanitizationSession


class SyntheticReportCorpus:
    identities = {
        'hostnames': ('hana-prod-01', 'app-prod-02'),
        'fqdns': ('hana-prod-01.customer.example',
                  'app-prod-02.customer.example'),
        'domain': 'customer.example',
        'ipv4': ('10.20.30.40', '10.20.30.41', '10.20.30.50'),
        'ipv6': ('2001:db8:abcd::10',),
        'mac': ('52:54:00:12:34:56', '52:54:00:12:34:57'),
        'emails': ('alice@customer.example', 'dbadmin@customer.example'),
        'usernames': ('alice', 'dbadmin'),
    }
    secrets = (
        'SyntheticSecret123', 'SyntheticSecret456', 'synthetic-api-token',
        'synthetic-bearer-token',
        'eyJsynthetic.header.signature',
        'AKIAABCDEFGHIJKLMNOP', 'ASIAABCDEFGHIJKLMNOP',
        'url-password-synthetic',
        '-----BEGIN PRIVATE KEY-----',
    )
    preserved = (
        'system_u:system_r:sshd_t:s0-s0:c0.c1023',
        'system_u:object_r:var_log_t:s0', 'sshd.service',
        'pacemaker.service', 'user.slice', 'user-1000.slice',
        'session-c33.scope', 'sshd', 'kernel-core-5.14.0-1.el9',
        'package-1.2.3', '22/tcp', 'ext4', 'defaults,_netdev',
        'mapper/vg_test-lv_root', 'UUID=11111111-2222-3333-4444-555555555555',
        'Resource TEST_HANA_00-clone: Started Promoted', 'cpu MHz : 2400',
        'MemTotal:       16384000 kB',
    )

    @classmethod
    def build_tree(cls, root):
        files = {
            'hostname': cls.identities['fqdns'][0] + '\n',
            'etc/hostname': cls.identities['hostnames'][1] + '\n',
            'etc/hosts': (
                '10.20.30.40 hana-prod-01.customer.example hana-prod-01\n'
                '10.20.30.41 app-prod-02.customer.example app-prod-02\n'),
            'etc/fstab': (
                'UUID=11111111-2222-3333-4444-555555555555 '
                '/ ext4 defaults,_netdev 0 1\n'
                '/dev/mapper/vg_test-lv_root /var ext4 defaults 0 2\n'),
            'etc/resolv.conf': 'search customer.example\nnameserver 10.20.30.40\n',
            'etc/ssh/sshd_config': 'Port 22\nListen 22/tcp\nPermitRootLogin no\n',
            'etc/selinux/config': 'SELINUX=enforcing\n',
            'proc/cmdline': ('BOOT_IMAGE=/vmlinuz-5.14.0-1.el9 quiet '
                            'kernel-core-5.14.0-1.el9\n'),
            'proc/meminfo': 'MemTotal:       16384000 kB\n',
            'proc/cpuinfo': 'model name : Synthetic CPU\ncpu MHz : 2400\n',
            'sos_commands/networking/ip_-o_addr': (
                '2: eno1 inet 10.20.30.40/24 brd 10.20.30.255 '
                'scope global\n'
                '2: eno1 inet6 2001:db8:abcd::10/64 scope global '
                'link/ether 52:54:00:12:34:56\n'
                '3: bond0 inet 10.20.30.41/24 link/ether '
                '52:54:00:12:34:57\n'),
            'sos_commands/networking/ip_addr': 'inet 10.20.30.40/24\n',
            'sos_commands/networking/ip_route': (
                'default via 10.20.30.50 dev eno1\n'),
            'sos_commands/networking/ip_neigh': '10.20.30.41 dev eno1 lladdr 52:54:00:12:34:57\n',
            'sos_commands/networking/ss': 'LISTEN 0 128 10.20.30.40:22 0.0.0.0:*\n',
            'sos_commands/networking/nmconnection': (
                'address1=10.20.30.40/24,10.20.30.50\n'
                'dns=10.20.30.41;\n'),
            'sos_commands/selinux/avc': (
                'type=AVC avc: denied { read } for '
                'scontext=system_u:system_r:sshd_t:s0-s0:c0.c1023 '
                'tcontext=system_u:object_r:var_log_t:s0 tclass=file\n'),
            'sos_commands/auditd/audit.log': (
                'type=USER_LOGIN acct="alice" AUID="alice" UID="alice" '
                'user=alice ruser=alice\n'
                'type=USER_LOGIN acct="dbadmin" AUID="dbadmin"\n'
                'OUID="root" OGID="root" AUID="unset" UID="root"\n'),
            'var/log/auth.log': (
                'sshd[123]: Accepted publickey for alice from 10.20.30.40 port 22\n'
                'pam_unix(sshd:session): session opened for user dbadmin(uid=1001)\n'
                'sudo: alice : command=/usr/bin/systemctl restart sshd.service\n'
                'contact alice@customer.example and dbadmin@customer.example\n'),
            'var/log/journal.log': (
                'systemd[1]: Started sshd.service\n'
                'user-1000.slice session-c33.scope user.slice\n'),
            'sos_commands/systemd/systemctl_status': 'pacemaker.service active (running)\n',
            'sos_commands/process/ps': 'root 123 sshd --foreground\nalice 456 hana-worker\n',
            'sos_commands/kernel/uname': 'Linux hana-prod-01 5.14.0-1.el9 x86_64\n',
            'sos_commands/kernel/vmstat': 'r b swpd free 1 0 0 8192\n',
            'sos_commands/filesys/df': '/dev/mapper/vg_test-lv_root 100G 20G 80G 20% /var\n',
            'sos_commands/multipath/multipath_ll': 'mpatha (3600508b400105e210000900000490000) dm-0\n',
            'sos_commands/sap/hana_replication': (
                'SID TEST instance 00 host hana-prod-01.customer.example '
                'secondary app-prod-02.customer.example state=ACTIVE VIP=10.20.30.50\n'),
            'sos_commands/pacemaker/crm_mon': (
                'Node: hana-prod-01.customer.example\n'
                'Resource TEST_HANA_00-clone: Started Promoted\n'),
            'details/secrets.txt': (
                'password=SyntheticSecret123\npasswd=SyntheticSecret456\n'
                'token=synthetic-api-token\n'
                'Authorization: Bearer synthetic-bearer-token\n'
                'jwt=eyJsynthetic.header.signature\n'
                'aws=AKIAABCDEFGHIJKLMNOP\naws2=ASIAABCDEFGHIJKLMNOP\n'
                'url=https://alice:url-password-synthetic@customer.example/x\n'
                '-----BEGIN PRIVATE KEY-----\n'),
            'details/edge.txt': '',
            'details/no-newline.txt': 'truncated audit acct="alice"',
            'details/crlf.txt': 'package-1.2.3\r\nPort 22\r\n',
            'details/long.txt': 'technical-' + ('x' * 10000),
            'details/malformed-but-text.txt': 'incomplete journal record [still utf8]\n',
        }
        for relative, content in files.items():
            path = Path(root) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')

    @classmethod
    def build_archive(cls, root, archive_path):
        with tarfile.open(archive_path, 'w:xz') as archive:
            archive.add(root, arcname='sosreport-synthetic')


class ReportCorpusTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.tree = self.root / 'tree'
        self.tree.mkdir()
        SyntheticReportCorpus.build_tree(self.tree)
        self.input = self.root / 'input.tar.xz'
        self.output = self.root / 'sanitized.tar.xz'
        self.mapping = self.root / 'private-map.json'
        SyntheticReportCorpus.build_archive(self.tree, self.input)

    def tearDown(self):
        self.work.cleanup()

    def run_pipeline(self, mapping=True):
        return ReportSanitizer(
            hostnames=SyntheticReportCorpus.identities['fqdns'] +
            SyntheticReportCorpus.identities['hostnames'],
            domains=(SyntheticReportCorpus.identities['domain'],),
            usernames=SyntheticReportCorpus.identities['usernames'],
            temp_parent=self.root).sanitize(
                self.input, self.output,
                mapping_output=self.mapping if mapping else None)

    def archive_bytes(self):
        values = []
        with tarfile.open(self.output, 'r:xz') as archive:
            for member in archive:
                values.append(member.name.encode())
                if member.isfile():
                    values.append(archive.extractfile(member).read())
                elif member.issym():
                    values.append(member.linkname.encode())
        return b'\n'.join(values)

    def test_complete_corpus_privacy_oracle_and_mapping(self):
        input_bytes = self.input.read_bytes()
        result = self.run_pipeline()
        data = self.archive_bytes()
        private = list(SyntheticReportCorpus.identities['hostnames'])
        private += list(SyntheticReportCorpus.identities['fqdns'])
        private += [SyntheticReportCorpus.identities['domain']]
        private += list(SyntheticReportCorpus.identities['ipv4'])
        private += list(SyntheticReportCorpus.identities['ipv6'])
        private += list(SyntheticReportCorpus.identities['mac'])
        private += list(SyntheticReportCorpus.identities['emails'])
        private += list(SyntheticReportCorpus.identities['usernames'])
        for value in private + list(SyntheticReportCorpus.secrets):
            self.assertNotIn(value.encode(), data, value)
        self.assertEqual(input_bytes, self.input.read_bytes())
        self.assertIn(b'[REDACTED_SECRET]', data)
        self.assertIn(b'[REDACTED_TOKEN]', data)
        self.assertTrue(result['mapping_written'])
        self.assertEqual(self.mapping.stat().st_mode & 0o777, 0o600)
        with self.mapping.open(encoding='utf-8') as stream:
            mapping = json.load(stream)
        self.assertNotIn(self.mapping.name.encode(), data)
        self.assertEqual(mapping['schema_version'], 1)
        self.assertEqual(mapping['hostnames']['hana-prod-01'],
                         mapping['hostnames']['hana-prod-01'])

    def test_preservation_summary(self):
        self.run_pipeline(mapping=False)
        data = self.archive_bytes().decode('utf-8', errors='strict')
        for value in SyntheticReportCorpus.preserved:
            self.assertIn(value, data, value)
        self.assertNotIn('customer.example', data)
        self.assertNotIn('hana-prod-01', data)

    def test_cross_file_distinct_aliases_and_counts(self):
        result = self.run_pipeline()
        with self.mapping.open(encoding='utf-8') as stream:
            mapping = json.load(stream)
        for namespace, originals in (
                ('hostnames', SyntheticReportCorpus.identities['hostnames']),
                ('ipv4', SyntheticReportCorpus.identities['ipv4']),
                ('mac', SyntheticReportCorpus.identities['mac']),
                ('emails', SyntheticReportCorpus.identities['emails']),
                ('usernames', SyntheticReportCorpus.identities['usernames'])):
            if namespace == 'ipv4':
                aliases = [mapping[namespace][key]
                           for key in mapping[namespace]
                           if key.split('/', 1)[0] in originals]
            else:
                aliases = [mapping[namespace][value] for value in originals
                           if value in mapping[namespace]]
            self.assertEqual(len(aliases), len(set(aliases)), namespace)
            self.assertGreaterEqual(len(aliases), 2 if len(originals) > 1 else 1)
            self.assertEqual(result['mapping_entries'][namespace],
                             len(mapping[namespace]))

    def test_direct_and_normal_nested_report_roots_match(self):
        direct_work = self.root / 'direct-work'
        direct_work.mkdir()
        direct_session = SanitizationSession(
            direct_work,
            hostnames=SyntheticReportCorpus.identities['fqdns'] +
            SyntheticReportCorpus.identities['hostnames'],
            domains=(SyntheticReportCorpus.identities['domain'],),
            usernames=SyntheticReportCorpus.identities['usernames'])
        direct_summary = ReportIdentityDiscovery(
            self.tree, direct_session).discover()
        direct_manifest = SoSMappingManifest.from_session(direct_session)

        result = self.run_pipeline(mapping=False)
        self.assertEqual(result['discovered'], direct_manifest.summary())
        self.assertEqual(direct_summary['hostnames'], 2)
        self.assertEqual(direct_summary['ipv4'], 5)
        self.assertEqual(direct_summary['ipv6'], 2)
        self.assertEqual(direct_summary['mac'], 2)
        self.assertEqual(direct_summary['usernames'], 2)
        self.assertEqual(direct_summary['emails'], 2)

    def test_ambiguous_extracted_roots_fail_closed(self):
        ambiguous = self.root / 'ambiguous'
        ambiguous.mkdir()
        (ambiguous / 'one').mkdir()
        (ambiguous / 'two').mkdir()
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer._select_report_root(ambiguous)
        (ambiguous / 'two').rmdir()
        (ambiguous / 'top-level-file').write_text('x', encoding='utf-8')
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer._select_report_root(ambiguous)

    def test_path_and_symlink_policy_is_explicit(self):
        self.run_pipeline(mapping=False)
        with tarfile.open(self.output, 'r:xz') as archive:
            names = [member.name for member in archive]
        self.assertIn('sosreport-synthetic/details/secrets.txt', names)
        # Phase 15 rejects archive symlink members, so the positive corpus
        # remains link-free; link behavior is covered by lower-level tests.
        linked = self.root / 'linked-tree'
        linked.mkdir()
        (linked / 'target').write_text('safe', encoding='utf-8')
        (linked / 'link').symlink_to('target')
        linked_archive = self.root / 'linked.tar.xz'
        SyntheticReportCorpus.build_archive(linked, linked_archive)
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                linked_archive, self.root / 'linked-out.tar.xz')

    def test_malformed_and_invalid_utf8_policy(self):
        self.run_pipeline(mapping=False)
        invalid = self.root / 'invalid-tree'
        invalid.mkdir()
        (invalid / 'file').write_bytes(b'valid\xff')
        invalid_archive = self.root / 'invalid.tar.xz'
        with tarfile.open(invalid_archive, 'w:xz') as archive:
            archive.add(invalid, arcname='report')
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                invalid_archive, self.root / 'invalid-out.tar.xz')

    def test_negative_archive_inputs_publish_nothing(self):
        cases = {
            'traversal': [('../../escape', b'x')],
            'absolute': [('/etc/passwd', b'x')],
        }
        for name, members in cases.items():
            archive_path = self.root / (name + '.tar.xz')
            with tarfile.open(archive_path, 'w:xz') as archive:
                for member_name, content in members:
                    info = tarfile.TarInfo(member_name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            output = self.root / (name + '-out.tar.xz')
            with self.assertRaises(ReportSanitizerError):
                ReportSanitizer(temp_parent=self.root).sanitize(
                    archive_path, output)
            self.assertFalse(output.exists())

    def test_default_run_has_no_mapping_and_existing_output_is_untouched(self):
        self.run_pipeline(mapping=False)
        self.assertFalse(self.mapping.exists())
        existing = self.root / 'existing.tar.xz'
        existing.write_bytes(b'keep')
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(self.input, existing)
        self.assertEqual(existing.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
