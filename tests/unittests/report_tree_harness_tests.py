import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import ReportTreeResidualError
from tests.tools import run_tree_residual
from tests.tools.run_tree_residual import validate_private_tree
from sos.cleaner.filesystem import remove_private_tree


class ReportTreeHarnessTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.staging = self.root / 'sanitized-tree'
        self.staging.mkdir()
        self.staging.chmod(0o700)
        self.mapping = self.root / 'mapping.json'
        manifest = SoSMappingManifest({
            'hostnames': {'host.example': 'host0'},
            'domains': {},
            'ipv4': {'10.20.30.40': '10.0.0.1'},
            'ipv6': {},
            'mac': {},
            'emails': {},
            'usernames': {},
        })
        self.mapping.write_text(json.dumps({
            'schema_version': 1, **manifest.raw_mappings()},
            sort_keys=True), encoding='utf-8')
        self.mapping.chmod(0o600)

    def tearDown(self):
        self.work.cleanup()

    def test_private_harness_uses_production_validator_and_safe_context(self):
        cases = (
            ('host.txt', 'host.example', 'known hostname'),
            ('address.txt', '10.20.30.40', 'known ipv4'),
            ('secret.txt', 'password=unresolved', 'generic secret'),
        )
        for relative, content, category in cases:
            with self.subTest(relative=relative):
                path = self.staging / relative
                path.write_text(content, encoding='utf-8')
                try:
                    validate_private_tree(self.staging, self.mapping)
                except ReportTreeResidualError as error:
                    self.assertEqual(
                        error.category,
                        'generic residual' if category == 'generic secret'
                        else category)
                    self.assertEqual(error.relative_path, (relative,))
                else:
                    self.fail('expected residual failure')
                path.unlink()

    def test_private_contract_rejects_insecure_inputs(self):
        self.staging.chmod(0o755)
        with self.assertRaises(ValueError):
            validate_private_tree(self.staging, self.mapping)
        self.staging.chmod(0o700)
        self.mapping.chmod(0o644)
        with self.assertRaises(ValueError):
            validate_private_tree(self.staging, self.mapping)

    def test_checkpoint_refuses_wrong_source_binding(self):
        checkpoint = self.root / 'checkpoint'
        checkpoint.mkdir(mode=0o700)
        (checkpoint / 'tree').mkdir(mode=0o700)
        (checkpoint / 'session-manifest.json').write_text('{}',
                                                           encoding='utf-8')
        (checkpoint / 'session-manifest.json').chmod(0o600)
        source = self.root / 'source.tar.xz'
        source.write_bytes(b'source')
        metadata = {
            'source_archive': str(source),
            'source_sha256': 'wrong',
            'git_head': 'unused',
            'worktree_fingerprint': 'unused',
            'mapping_schema_version': 1,
            'mapping_frozen': True,
        }
        (checkpoint / 'checkpoint-metadata.json').write_text(
            json.dumps(metadata), encoding='utf-8')
        (checkpoint / 'checkpoint-metadata.json').chmod(0o600)
        with self.assertRaises(ValueError):
            run_tree_residual.validate_checkpoint(checkpoint)

    def test_checkpoint_refuses_code_binding_mismatch(self):
        checkpoint = self.root / 'checkpoint'
        checkpoint.mkdir(mode=0o700)
        (checkpoint / 'tree').mkdir(mode=0o700)
        (checkpoint / 'session-manifest.json').write_text('{}',
                                                           encoding='utf-8')
        (checkpoint / 'session-manifest.json').chmod(0o600)
        source = self.root / 'source.tar.xz'
        source.write_bytes(b'source')
        metadata = {
            'source_archive': str(source),
            'source_sha256': run_tree_residual._sha256(source),
            'git_head': 'wrong-head',
            'worktree_fingerprint': 'wrong-fingerprint',
            'mapping_schema_version': 1,
            'mapping_frozen': True,
        }
        (checkpoint / 'checkpoint-metadata.json').write_text(
            json.dumps(metadata), encoding='utf-8')
        (checkpoint / 'checkpoint-metadata.json').chmod(0o600)
        with self.assertRaises(ValueError):
            run_tree_residual.validate_checkpoint(checkpoint)

    def test_production_fingerprint_covers_recursive_cleaner_sources(self):
        root = Path(self.work.name) / 'checkout'
        files = (
            'sos/cleaner/parsers/ipv6_parser.py',
            'sos/cleaner/mappings/ipv6_map.py',
            'sos/cleaner/tree.py',
            'sos/cleaner/report_residual.py',
            'sos/cleaner/corosync.py',
        )
        for relative in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic source\n', encoding='utf-8')
        baseline = run_tree_residual.production_fingerprint(root)
        self.assertEqual(baseline,
                         run_tree_residual.production_fingerprint(root))
        for relative in files:
            path = root / relative
            original = path.read_text(encoding='utf-8')
            path.write_text(original + 'changed\n', encoding='utf-8')
            self.assertNotEqual(
                baseline, run_tree_residual.production_fingerprint(root),
                relative)
            path.write_text(original, encoding='utf-8')
        docs = root / 'docs' / 'note.md'
        metadata = root / 'private-checkpoint-metadata.json'
        docs.parent.mkdir(parents=True)
        docs.write_text('one\n', encoding='utf-8')
        metadata.write_text('one\n', encoding='utf-8')
        unchanged = run_tree_residual.production_fingerprint(root)
        docs.write_text('two\n', encoding='utf-8')
        metadata.write_text('two\n', encoding='utf-8')
        self.assertEqual(unchanged,
                         run_tree_residual.production_fingerprint(root))

    def test_remove_private_tree_handles_read_only_directories_and_symlinks(self):
        private = Path(self.work.name) / 'private-tree'
        nested = private / 'one' / 'two' / 'three'
        nested.mkdir(parents=True)
        (nested / 'file').write_text('private', encoding='utf-8')
        external = Path(self.work.name) / 'external'
        external.write_text('keep', encoding='utf-8')
        (private / 'inside-link').symlink_to('one')
        (private / 'outside-link').symlink_to(external)
        for directory in (private, private / 'one', private / 'one' / 'two',
                          nested):
            directory.chmod(0o555)

        remove_private_tree(private)

        self.assertFalse(private.exists())
        self.assertEqual(external.read_text(encoding='utf-8'), 'keep')


if __name__ == '__main__':
    unittest.main()
