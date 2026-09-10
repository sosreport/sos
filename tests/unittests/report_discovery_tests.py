import tempfile
import unittest
from pathlib import Path

from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.session import SanitizationSession


class ReportDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tree = tempfile.TemporaryDirectory()
        self.session_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tree.name)
        self.session = SanitizationSession(
            self.session_dir.name,
            hostnames=('seedhost',), domains=('sensitive.example',),
            usernames=('seeduser',))

    def tearDown(self):
        self.session_dir.cleanup()
        self.tree.cleanup()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def test_structured_sources_and_restricted_fqdns(self):
        self.write('hostname', 'node.sensitive.example\n')
        self.write('etc/hostname', 'etcnode\n')
        self.write('etc/hosts',
                   '10.20.30.40 node.sensitive.example node\n'
                   '192.0.2.10 unrelated.example\n')
        self.write('sos_commands/networking/ip_-o_addr',
                   '2: eth0 inet 10.20.30.40/24 brd 10.20.30.255 '
                   'scope global\n'
                   '2: eth0 inet6 2001:db8:1::10/64 scope global\n'
                   '2: eth0 link/ether 12:34:56:78:90:ab brd ff:ff:ff:ff:ff:ff\n')
        self.write('sos_commands/networking/ip_route',
                   'default via 10.20.30.1 dev eth0 src 10.20.30.40\n')
        self.write('var/log/audit/audit.log',
                   'type=USER_LOGIN acct="audituser" '
                   'email=audit.user@example.test\n')

        summary = ReportIdentityDiscovery(self.root, self.session).discover()

        self.assertIn('node', self.session.hostname_parser.mapping.dataset)
        self.assertIn('node.sensitive.example',
                      self.session.hostname_parser.mapping.dataset)
        self.assertNotIn('unrelated.example',
                         self.session.hostname_parser.mapping.dataset)
        self.assertIn('audituser', self.session.username_parser.mapping.dataset)
        self.assertGreaterEqual(summary['hostnames'], 4)
        self.assertGreaterEqual(summary['ipv4'], 2)
        self.assertGreaterEqual(summary['ipv6'], 1)
        self.assertEqual(summary['mac'], 1)
        self.assertEqual(summary['emails'], 1)

    def test_conservative_lines_and_missing_files(self):
        self.write('hostname', 'package-1.2.3.4\n')
        self.write('etc/hosts',
                   '127.0.0.1 localhost localhost.localdomain\n'
                   '10.0.0.2 system_u:system_r:sshd_t:s0\n')
        self.write('sos_commands/networking/ip_-o_addr',
                   'malformed 999.999.999.999 not-an-address\n')
        discovery = ReportIdentityDiscovery(self.root, self.session)
        summary = discovery.discover()
        self.assertNotIn('package-1.2.3.4',
                         self.session.hostname_parser.mapping.dataset)
        self.assertNotIn('system_u', self.session.hostname_parser.mapping.dataset)
        self.assertNotIn('sshd_t', self.session.hostname_parser.mapping.dataset)
        self.assertEqual(summary['emails'], 0)

    def test_secrets_not_collected_and_sessions_isolated(self):
        self.write('var/log/auth.log',
                   'password="secret-value" user="visibleuser"\n')
        ReportIdentityDiscovery(self.root, self.session).discover()
        state = repr(self.session.mappings)
        self.assertNotIn('secret-value', state)
        self.assertIn('visibleuser', self.session.username_parser.mapping.dataset)

        other_dir = tempfile.TemporaryDirectory()
        self.addCleanup(other_dir.cleanup)
        other = SanitizationSession(other_dir.name)
        self.assertNotIn('visibleuser', other.username_parser.mapping.dataset)

    def test_explicit_seed_is_preserved(self):
        ReportIdentityDiscovery(self.root, self.session).discover()
        self.assertIn('seedhost', self.session.hostname_parser.mapping.dataset)
        self.assertIn('seeduser', self.session.username_parser.mapping.dataset)
        self.assertIn('sensitive.example',
                      self.session.hostname_parser.mapping.dataset)


if __name__ == '__main__':
    unittest.main()
