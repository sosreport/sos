import tempfile
import unittest

from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.session import SanitizationSession


class MappingManifestTests(unittest.TestCase):
    def make_session(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return SanitizationSession(
            directory.name,
            hostnames=('node',), domains=('customer.example',),
            usernames=('alice',))

    def populate(self, session):
        session.sanitize_line(
            'node.customer.example customer.example '
            '10.20.30.40 2001:db8:1::10 12:34:56:78:90:ab '
            'alice@example.test acct=alice')

    def test_correlations_and_schema(self):
        session = self.make_session()
        self.populate(session)
        manifest = SoSMappingManifest.from_session(session)
        raw = manifest.raw_mappings()

        self.assertEqual(raw['schema_version'], 1)
        self.assertEqual(raw['hostnames']['node'], 'host0')
        self.assertEqual(raw['domains']['customer.example'],
                         'obfuscateddomain0.example')
        self.assertEqual(raw['emails']['alice@example.test'],
                         'user0@obfuscateddomain0.example')
        self.assertIn('10.20.30.40', raw['ipv4'])
        self.assertIn('2001:db8:1::10', raw['ipv6'])
        self.assertIn('12:34:56:78:90:ab', raw['mac'])
        self.assertEqual(raw['usernames']['alice'], 'obfuscateduser0')

    def test_repeated_and_generated_values(self):
        session = self.make_session()
        self.populate(session)
        self.populate(session)
        manifest = SoSMappingManifest.from_session(session)
        raw = manifest.raw_mappings()
        for mappings in raw.values():
            if isinstance(mappings, dict):
                for original in mappings:
                    self.assertFalse(original.startswith('obfuscated'))
                    self.assertFalse(original.startswith('user0@'))
        self.assertEqual(len(raw['emails']), 1)

    def test_summary_is_counts_only(self):
        session = self.make_session()
        self.populate(session)
        summary = SoSMappingManifest.from_session(session).summary()
        self.assertTrue(all(isinstance(value, int)
                            for value in summary.values()))
        self.assertNotIn('alice@example.test', repr(summary))
        self.assertNotIn('obfuscateduser0', repr(summary))

    def test_manifest_does_not_mutate_session_or_share_between_sessions(self):
        first = self.make_session()
        self.populate(first)
        before = repr(first.mappings)
        first_manifest = SoSMappingManifest.from_session(first)
        self.assertEqual(before, repr(first.mappings))

        second = self.make_session()
        second_manifest = SoSMappingManifest.from_session(second)
        self.assertNotEqual(first_manifest.summary(), second_manifest.summary())
        self.assertEqual(second_manifest.summary()['hostnames'], 1)

    def test_secrets_are_absent(self):
        session = self.make_session()
        session.sanitize_line(
            'password="secret-value" token=secret-token '
            'eyJheader.payload.signature')
        raw = SoSMappingManifest.from_session(session).raw_mappings()
        serialized = repr(raw)
        for secret in ('secret-value', 'secret-token', 'eyJheader.payload.signature'):
            self.assertNotIn(secret, serialized)


if __name__ == '__main__':
    unittest.main()
