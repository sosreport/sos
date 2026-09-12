import tempfile
import unittest
from io import BytesIO

from sos.cleaner.session import (SanitizationSession,
                                  SessionMappingFrozenError,
                                  SessionStageError)
from sos.cleaner.text import sanitize_stream


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

    def test_known_contiguous_mac_representation_is_replaced(self):
        session = self.session()
        session.sanitize_line('mac=aa:bb:cc:dd:ee:ff')
        session.freeze_mappings()
        result = session.sanitize_line('mac=aabbccddeeff')
        self.assertEqual(result, 'mac=53:4f:53:00:00:01')

    def test_unknown_contiguous_mac_is_not_discovered_or_partially_replaced(self):
        session = self.session()
        session.freeze_mappings()
        value = 'aabbccddeeff'
        self.assertEqual(session.sanitize_line(value), value)
        self.assertEqual(session.sanitize_line('x' + value + '0'),
                         'x' + value + '0')

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

    def test_secret_state_isolated_between_independent_streams(self):
        session = self.session(hostnames=('node',), usernames=('alice',))
        first = BytesIO()
        sanitize_stream(BytesIO(b'password="unfinished\n'), first,
                        session=session,
                        redactor=session.new_stream_redactor())
        self.assertEqual(first.getvalue(), b'password="[REDACTED_SECRET]\n')

        second = BytesIO()
        sanitize_stream(BytesIO(b'systemd.service port=22\n'), second,
                        session=session,
                        redactor=session.new_stream_redactor())
        self.assertEqual(second.getvalue(), b'systemd.service port=22\n')
        self.assertEqual(session.hostname_parser.mapping.dataset['node'],
                         'host0')

    def test_clean_text_stream_state_remains_continuous(self):
        session = self.session()
        output = BytesIO()
        sanitize_stream(BytesIO(b'password="unfinished\ncontinued\n'),
                        output, session=session)
        self.assertEqual(output.getvalue(),
                         b'password="[REDACTED_SECRET]\n\n')

    def test_frozen_session_rejects_new_username_mapping(self):
        session = self.session()
        session.freeze_mappings()
        self.assertTrue(session.mappings_frozen)
        with self.assertRaises(SessionMappingFrozenError):
            session.add_username('lateuser')
        with self.assertRaises(SessionStageError):
            session.sanitize_line('user=lateuser\n')

    def test_frozen_session_rejects_new_ip_mapping(self):
        session = self.session()
        session.freeze_mappings()
        with self.assertRaises(SessionMappingFrozenError):
            session.add_ip('10.20.30.40')

    def test_frozen_session_rejects_new_email_mapping(self):
        session = self.session()
        session.freeze_mappings()
        with self.assertRaises(SessionStageError):
            session.sanitize_line('lateuser@example.test\n')


if __name__ == '__main__':
    unittest.main()
