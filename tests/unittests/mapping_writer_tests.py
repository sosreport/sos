import json
import os
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.mapping_writer import (MappingManifestWriter,
                                         MappingManifestWriterError)
from sos.cleaner.session import SanitizationSession


class MappingWriterTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        (self.root / 'session').mkdir()
        self.session = SanitizationSession(
            self.root / 'session', hostnames=('node',),
            domains=('customer.example',), usernames=('alice',))
        self.session.sanitize_line(
            'node customer.example 10.20.30.40 2001:db8::10 '
            '12:34:56:78:90:ab alice alice@example.test')
        self.manifest = SoSMappingManifest.from_session(self.session)

    def tearDown(self):
        self.work.cleanup()

    def destination(self, name='mapping.json'):
        return self.root / name

    def test_serializes_deterministically_and_mode_0600(self):
        destination = self.destination()
        MappingManifestWriter(self.manifest, destination).write()
        raw = json.loads(destination.read_text(encoding='utf-8'))
        self.assertEqual(raw['schema_version'], 1)
        self.assertEqual(list(raw)[1:], list(self.manifest.namespaces))
        self.assertEqual(raw['hostnames']['node'], 'host0')
        self.assertEqual(stat_mode(destination), 0o600)
        first = destination.read_bytes()
        destination.unlink()
        MappingManifestWriter(self.manifest, destination).write()
        self.assertEqual(destination.read_bytes(), first)

    def test_excludes_secrets_generated_keys_and_internal_state(self):
        self.session.sanitize_line(
            'password=secret-value Bearer token eyJheader.payload.signature')
        destination = self.destination()
        MappingManifestWriter(SoSMappingManifest.from_session(self.session),
                               destination).write()
        serialized = destination.read_text(encoding='utf-8')
        for value in ('secret-value', 'Bearer', 'eyJheader.payload.signature',
                      'name_count', 'cache'):
            self.assertNotIn(value, serialized)
        self.assertNotIn('obfuscateduser0',
                         repr(json.loads(serialized)['usernames'].keys()))

    def test_existing_destination_and_publication_race_fail_closed(self):
        destination = self.destination()
        destination.write_text('keep', encoding='utf-8')
        with self.assertRaises(MappingManifestWriterError):
            MappingManifestWriter(self.manifest, destination).write()
        self.assertEqual(destination.read_text(), 'keep')
        destination.unlink()

        class RaceWriter(MappingManifestWriter):
            def _publish_noreplace(inner, temporary):
                destination.write_text('keep-race', encoding='utf-8')
                super()._publish_noreplace(temporary)

        with self.assertRaises(MappingManifestWriterError):
            RaceWriter(self.manifest, destination).write()
        self.assertEqual(destination.read_text(), 'keep-race')
        self.assertFalse(any(path.name.startswith('.sos-mapping-')
                             for path in self.root.iterdir()))

    def test_manifest_is_not_mutated(self):
        before = self.manifest.raw_mappings()
        MappingManifestWriter(self.manifest, self.destination()).write()
        self.assertEqual(before, self.manifest.raw_mappings())


def stat_mode(path):
    return os.stat(path, follow_symlinks=False).st_mode & 0o777


if __name__ == '__main__':
    unittest.main()
