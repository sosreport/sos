import bz2
import io
import os
import tempfile
import unittest

from sos.cleaner.pacemaker import (PacemakerSchedulerInput,
                                   PacemakerSchedulerInputError)
from sos.cleaner.session import SanitizationSession


class PacemakerSchedulerInputTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.session = SanitizationSession(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def compressed(self, payload):
        value = bz2.compress(payload, compresslevel=1)
        return io.BytesIO(value), len(value)

    def test_path_grammar(self):
        accepted = (
            'sos_commands/pacemaker/crm_report/node/pengine/pe-input-0.bz2',
            'root/sos_commands/pacemaker/crm_report/node/pengine/'
            'pe-input-2147483647.bz2',
        )
        rejected = (
            'sos_commands/pacemaker/crm_report/node/pengine/pe-input-01.bz2',
            'sos_commands/pacemaker/crm_report/node/pengine/pe-input-2147483648.bz2',
            'sos_commands/pacemaker/crm_report/node/pengine/pe-input-1x.bz2',
            'sos_commands/pacemaker/crm_report/node/pengine/pe-warn-1.bz2',
            'sos_commands/pacemaker/crm_report/node/pengine/pe-input-1.bz2/x',
            'root/root/sos_commands/pacemaker/crm_report/node/pengine/'
            'pe-input-1.bz2',
        )
        for path in accepted:
            self.assertTrue(PacemakerSchedulerInput.is_path(path), path)
        for path in rejected:
            self.assertFalse(PacemakerSchedulerInput.is_path(path), path)

    def test_xml_credentials_are_redacted_before_mapping(self):
        payload = (b'<cib><configuration><resources><primitive id="node">'
                   b'<instance_attributes><nvpair name="passwd" '
                   b'value="TOPSECRET"/><nvpair name="host" '
                   b'value="10.20.30.40"/></instance_attributes>'
                   b'</primitive></resources></configuration></cib>')
        source, size = self.compressed(payload)
        result = PacemakerSchedulerInput.sanitize(
            source, size, self.session)
        self.assertNotIn(b'TOPSECRET', result)
        self.assertIn(b'[REDACTED_SECRET]', result)
        self.assertEqual(self.session.summary()['ipv4'], 1)
        raw = self.session.mapping_manifest().raw_mappings()
        self.assertNotIn('TOPSECRET', repr(raw))

    def test_deterministic_recompression(self):
        payload = b'<cib><configuration/></cib>'
        self.assertEqual(PacemakerSchedulerInput.encode(payload),
                         PacemakerSchedulerInput.encode(payload))

    def test_invalid_xml_and_entities_fail_closed(self):
        for payload in (b'<not-cib/>', b'<cib>',
                        b'<!DOCTYPE cib [<!ENTITY x "y">]><cib/>'):
            with self.subTest(payload=payload):
                with self.assertRaises(PacemakerSchedulerInputError):
                    PacemakerSchedulerInput.prepare(payload)

    def test_bzip_trailing_and_concatenated_streams_fail_closed(self):
        payload = b'<cib><configuration/></cib>'
        value = bz2.compress(payload)
        for candidate in (value + b'x', value + value):
            with self.subTest(length=len(candidate)):
                with self.assertRaises(PacemakerSchedulerInputError):
                    PacemakerSchedulerInput.decode(io.BytesIO(candidate),
                                                   len(candidate))

    def test_bzip_limits_fail_closed(self):
        payload = b'<cib><configuration/></cib>'
        source, size = self.compressed(payload)
        old_compressed = PacemakerSchedulerInput.MAX_COMPRESSED
        old_decompressed = PacemakerSchedulerInput.MAX_DECOMPRESSED
        try:
            PacemakerSchedulerInput.MAX_COMPRESSED = size - 1
            with self.assertRaises(PacemakerSchedulerInputError):
                PacemakerSchedulerInput.decode(source, size)
            PacemakerSchedulerInput.MAX_COMPRESSED = 16 * 1024 * 1024
            PacemakerSchedulerInput.MAX_DECOMPRESSED = 1
            source, size = self.compressed(payload)
            with self.assertRaises(PacemakerSchedulerInputError):
                PacemakerSchedulerInput.decode(source, size)
        finally:
            PacemakerSchedulerInput.MAX_COMPRESSED = old_compressed
            PacemakerSchedulerInput.MAX_DECOMPRESSED = old_decompressed


if __name__ == '__main__':
    unittest.main()
