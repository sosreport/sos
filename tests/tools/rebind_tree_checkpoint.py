"""Safely migrate a legacy tree checkpoint to scoped fingerprint metadata."""

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from tests.tools.checkpoint_fingerprint import TREE_SCOPE, fingerprint


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def rebind(checkpoint):
    """Add scoped metadata without changing the materialized tree.

    This migration accepts only legacy checkpoints carrying the old full
    fingerprint, verifies the source binding and repository identity, and
    preserves that legacy value for audit.  The caller must have separately
    reviewed provenance showing that post-checkpoint changes were archive-only;
    no legacy digest is silently replaced.
    """
    checkpoint = Path(checkpoint).resolve()
    metadata_path = checkpoint / 'checkpoint-metadata.json'
    observed = os.lstat(metadata_path)
    if (not stat.S_ISREG(observed.st_mode) or observed.st_uid != os.geteuid()
            or observed.st_mode & 0o777 != 0o600):
        raise ValueError('metadata permissions')
    metadata = json.loads(metadata_path.read_text())
    if metadata.get('fingerprint_scope') is not None or \
            not isinstance(metadata.get('worktree_fingerprint'), str):
        raise ValueError('not a legacy checkpoint')
    source = metadata['source_archive']
    if metadata['source_sha256'] != _sha256(source):
        raise ValueError('source binding')
    root = Path(__file__).resolve().parents[2]
    import subprocess
    head = subprocess.check_output(
        ('git', '-C', str(root), 'rev-parse', 'HEAD'), text=True).strip()
    if metadata['git_head'] != head:
        raise ValueError('git identity')
    if not (checkpoint / 'tree').is_dir() or \
            not (checkpoint / 'session-manifest.json').is_file():
        raise ValueError('checkpoint incomplete')
    updated = dict(metadata)
    updated['legacy_worktree_fingerprint'] = metadata['worktree_fingerprint']
    updated.pop('worktree_fingerprint', None)
    updated['fingerprint_scope'] = TREE_SCOPE
    updated['fingerprint_sha256'] = fingerprint(root, TREE_SCOPE)
    fd, temporary = tempfile.mkstemp(
        prefix='.checkpoint-metadata-', dir=str(checkpoint))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            fd = None
            json.dump(updated, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, metadata_path)
        os.chmod(metadata_path, 0o600)
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.lexists(temporary):
            os.unlink(temporary)
    return updated


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('checkpoint')
    args = parser.parse_args()
    result = rebind(args.checkpoint)
    print(json.dumps({
        'fingerprint_scope': result['fingerprint_scope'],
        'fingerprint_sha256': result['fingerprint_sha256'],
        'legacy_worktree_fingerprint': result['legacy_worktree_fingerprint'],
    }, sort_keys=True))
