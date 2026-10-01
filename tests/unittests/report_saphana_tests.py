import tempfile
import unittest
from pathlib import Path

from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import ReportTreeResidualValidator
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer


class SapHanaReportTreeTests(unittest.TestCase):
    """Regression coverage for SAP HANA endpoint formatting."""

    def test_replication_info_slash_port_service_is_sanitized(self):
        with tempfile.TemporaryDirectory() as source_dir, \
                tempfile.TemporaryDirectory() as work_dir, \
                tempfile.TemporaryDirectory() as output_parent:
            source = Path(source_dir)
            target = source / 'sos_commands/saphana/RED_replicainfo'
            target.parent.mkdir(parents=True)
            local = '198.51.100.42'
            remote = '203.0.113.7'
            target.write_text(
                'System Replication Status\n'
                '  - channel : {<NetworkChannelBase>='
                f'{{local={local}/31001_tcp, '
                f'remote={remote}/54321_tcp, state=Connected}}}}\n',
                encoding='utf-8')
            address_file = source / 'sos_commands/networking/ip_-o_addr'
            address_file.parent.mkdir(parents=True, exist_ok=True)
            address_file.write_text(
                f'2: eth0 inet {local}/24 scope global\n',
                encoding='utf-8')

            session = SanitizationSession(work_dir)
            discovery = ReportIdentityDiscovery(source, session).discover()
            self.assertGreaterEqual(discovery['ipv4'], 1)
            destination = Path(output_parent) / 'tree'
            ReportTreeSanitizer(source, destination, session).sanitize()

            sanitized = target.relative_to(source)
            output = (destination / sanitized).read_text(encoding='utf-8')
            self.assertNotIn(local, output)
            self.assertNotIn(remote, output)
            self.assertIn('local=', output)
            self.assertIn('remote=', output)
            self.assertIn('state=Connected', output)
            manifest = SoSMappingManifest.from_session(session)
            result = ReportTreeResidualValidator(destination, manifest).validate()
            self.assertEqual(result['residual_failures'], 0)
