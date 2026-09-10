import tempfile
import unittest

from sos.cleaner.session import SanitizationSession


class SanitizationSessionTests(unittest.TestCase):
    def session(self, **kwargs):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return SanitizationSession(directory.name, **kwargs)

    def test_identity_mappings_are_stable(self):
        session = self.session(hostnames=('node',), domains=('customer.example',),
                               usernames=('alice',))
        values = (
            ('node', 'node'),
            ('node.customer.example', 'node.customer.example'),
            ('10.20.30.40', '10.20.30.40'),
            ('2607:c540:8c00:3318::34', '2607:c540:8c00:3318::34'),
            ('12:34:56:78:90:ab', '12:34:56:78:90:ab'),
            ('alice@example.test', 'alice@example.test'),
            ('acct=alice', 'acct=alice'),
        )
        for original, expected_input in values:
            first = session.sanitize_line(expected_input)
            second = session.sanitize_line(expected_input)
            self.assertEqual(first, second, original)
            self.assertNotEqual(first, expected_input, original)

    def test_sessions_do_not_share_state(self):
        first = self.session(hostnames=('node',))
        second = self.session(hostnames=('node',))
        self.assertEqual(first.sanitize_line('node'), 'host0')
        self.assertEqual(second.sanitize_line('node'), 'host0')
        self.assertIsNot(first.hostname_parser.mapping,
                         second.hostname_parser.mapping)
        self.assertIsNot(first.ipv6_parser.mapping.networks,
                         second.ipv6_parser.mapping.networks)

    def test_generated_aliases_are_protected(self):
        session = self.session(hostnames=('node',), usernames=('alice',))
        generated = session.sanitize_line(
            'node alice@example.test acct=alice 10.20.30.40')
        self.assertEqual(session.sanitize_line(generated), generated)

    def test_secrets_are_not_mapping_state(self):
        session = self.session(usernames=('alice',))
        session.sanitize_line('password="super-secret" token=abc123')
        state = repr(session.mappings)
        self.assertNotIn('super-secret', state)
        self.assertNotIn('abc123', state)
        self.assertIsNone(session.redactor._quote)


if __name__ == '__main__':
    unittest.main()
