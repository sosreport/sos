"""Deterministic fingerprints for materialized sanitizer stages."""

import hashlib
from pathlib import Path


FINGERPRINT_VERSION = 1
TREE_SCOPE = 'tree-v1'
ARCHIVE_SCOPE = 'archive-v1'

# This is a reviewed package-family boundary.  Every cleaner implementation
# file is tree-relevant by default; only these two archive-entry modules are
# excluded because they consume the already-materialized tree.
TREE_ARCHIVE_ONLY = frozenset({
    'sos/cleaner/archiver.py',
    'sos/cleaner/archive_residual.py',
})


def _files(root, scope):
    root = Path(root)
    files = sorted((root / 'sos' / 'cleaner').glob('**/*.py'))
    if scope == TREE_SCOPE:
        files = [path for path in files
                 if str(path.relative_to(root)) not in TREE_ARCHIVE_ONLY]
    elif scope != ARCHIVE_SCOPE:
        raise ValueError('unknown fingerprint scope')
    return files


def fingerprint(root, scope):
    """Hash sorted repository-relative names and file contents."""
    root = Path(root)
    digest = hashlib.sha256()
    for path in _files(root, scope):
        digest.update(str(path.relative_to(root)).encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()
