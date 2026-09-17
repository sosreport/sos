import tempfile
import unittest
from pathlib import Path

from tests.tools.checkpoint_fingerprint import (ARCHIVE_SCOPE, TREE_SCOPE,
                                                fingerprint)


class CheckpointFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        cleaner = self.root / 'sos' / 'cleaner'
        (cleaner / 'parsers').mkdir(parents=True)
        (cleaner / 'mappings').mkdir()
        for name in ('extractor.py', 'tree.py', 'filesystem.py',
                     'symlink.py', 'archiver.py', 'archive_residual.py',
                     'report_residual.py'):
            (cleaner / name).write_text(name)
        (cleaner / 'parsers' / 'sample.py').write_text('parser')
        (cleaner / 'mappings' / 'sample.py').write_text('mapping')

    def tearDown(self):
        self.work.cleanup()

    def test_tree_scope_excludes_archive_only_modules(self):
        baseline = fingerprint(self.root, TREE_SCOPE)
        (self.root / 'sos/cleaner/archiver.py').write_text('changed')
        self.assertEqual(baseline, fingerprint(self.root, TREE_SCOPE))
        (self.root / 'sos/cleaner/archive_residual.py').write_text('changed')
        self.assertEqual(baseline, fingerprint(self.root, TREE_SCOPE))

    def test_tree_scope_covers_relevant_recursive_modules(self):
        baseline = fingerprint(self.root, TREE_SCOPE)
        for path in ('extractor.py', 'tree.py', 'filesystem.py',
                     'symlink.py', 'report_residual.py',
                     'parsers/sample.py', 'mappings/sample.py'):
            target = self.root / 'sos/cleaner' / path
            target.write_text(target.read_text() + ' changed')
            self.assertNotEqual(baseline, fingerprint(self.root, TREE_SCOPE))

    def test_archive_scope_covers_both_archive_modules(self):
        baseline = fingerprint(self.root, ARCHIVE_SCOPE)
        for path in ('archiver.py', 'archive_residual.py'):
            target = self.root / 'sos/cleaner' / path
            target.write_text(target.read_text() + ' changed')
            self.assertNotEqual(baseline, fingerprint(self.root, ARCHIVE_SCOPE))

    def test_docs_do_not_affect_either_scope(self):
        baseline = (fingerprint(self.root, TREE_SCOPE),
                    fingerprint(self.root, ARCHIVE_SCOPE))
        (self.root / 'README').write_text('documentation')
        self.assertEqual(baseline, (fingerprint(self.root, TREE_SCOPE),
                                    fingerprint(self.root, ARCHIVE_SCOPE)))


if __name__ == '__main__':
    unittest.main()
