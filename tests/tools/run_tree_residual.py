#!/usr/bin/env python3
"""Run the production tree residual validator on a private staging tree.

This is a development aid. It deliberately accepts only a sanitizer-shaped,
owner-only staging directory and a mode-0600 private mapping manifest.
"""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import (ReportTreeResidualError,
                                         ReportTreeResidualValidator)
from tests.tools.checkpoint_fingerprint import (TREE_SCOPE, fingerprint)


def production_fingerprint(root=None):
    """Return the tree-stage fingerprint for compatibility."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    return fingerprint(root, TREE_SCOPE)


def git_head():
    root = Path(__file__).resolve().parents[2]
    return subprocess.check_output(
        ('git', '-C', str(root), 'rev-parse', 'HEAD'), text=True).strip()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _private_directory(path):
    path = os.path.abspath(path)
    observed = os.lstat(path)
    if not stat.S_ISDIR(observed.st_mode) or observed.st_uid != os.geteuid():
        raise ValueError
    if (observed.st_mode & 0o077 or
            os.path.basename(path) not in ('sanitized-tree', 'tree')):
        raise ValueError
    parent = os.stat(os.path.dirname(path), follow_symlinks=False)
    if parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
        raise ValueError
    if not os.listdir(path):
        raise ValueError
    return path


def _private_manifest(path):
    path = os.path.abspath(path)
    observed = os.lstat(path)
    if (not stat.S_ISREG(observed.st_mode) or observed.st_uid != os.geteuid()
            or observed.st_mode & 0o077 != 0o000):
        raise ValueError
    if observed.st_mode & 0o777 != 0o600:
        raise ValueError
    with open(path, encoding='utf-8') as stream:
        data = json.load(stream)
    expected = {'schema_version', *SoSMappingManifest.namespaces}
    if set(data) != expected or data.get('schema_version') != \
            SoSMappingManifest.schema_version:
        raise ValueError
    if any(not isinstance(data[name], dict) for name in
           SoSMappingManifest.namespaces):
        raise ValueError
    if any(not isinstance(key, str) or not isinstance(value, str)
           for name in SoSMappingManifest.namespaces
           for key, value in data[name].items()):
        raise ValueError
    return SoSMappingManifest(data)


def validate_checkpoint(checkpoint):
    checkpoint = os.path.abspath(checkpoint)
    observed = os.lstat(checkpoint)
    if (not stat.S_ISDIR(observed.st_mode) or observed.st_uid != os.geteuid()
            or observed.st_mode & 0o077):
        raise ValueError
    metadata_path = os.path.join(checkpoint, 'checkpoint-metadata.json')
    metadata_stat = os.lstat(metadata_path)
    if (not stat.S_ISREG(metadata_stat.st_mode) or
            metadata_stat.st_uid != os.geteuid() or
            metadata_stat.st_mode & 0o777 != 0o600):
        raise ValueError
    with open(metadata_path, encoding='utf-8') as stream:
        metadata = json.load(stream)
    source = metadata['source_archive']
    if (metadata['source_sha256'] != _sha256(source) or
            metadata['git_head'] != git_head() or
            metadata.get('fingerprint_scope') != TREE_SCOPE or
            metadata.get('fingerprint_sha256') != production_fingerprint() or
            metadata['mapping_schema_version'] !=
            SoSMappingManifest.schema_version or
            metadata.get('mapping_frozen') is not True):
        raise ValueError
    tree = os.path.join(checkpoint, 'tree')
    mapping = os.path.join(checkpoint, 'session-manifest.json')
    return tree, mapping


def validate_private_tree(staging, mapping):
    """Validate using the production validator and return its safe summary."""
    staging = _private_directory(staging)
    manifest = _private_manifest(mapping)
    return ReportTreeResidualValidator(staging, manifest).validate()


def main(argv=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--checkpoint')
    group.add_argument('--staging')
    parser.add_argument('--mapping')
    args = parser.parse_args(argv)
    try:
        if args.checkpoint:
            staging, mapping = validate_checkpoint(args.checkpoint)
        elif args.mapping:
            staging, mapping = args.staging, args.mapping
        else:
            parser.error('--mapping is required with --staging')
        summary = validate_private_tree(staging, mapping)
    except ReportTreeResidualError as error:
        result = {'status': 'residual_failure',
                  'category': error.category,
                  'relative_path': '/'.join(error.relative_path or ())}
        print(json.dumps(result, sort_keys=True))
        return 1
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({'status': 'invalid_private_input'}, sort_keys=True))
        return 2
    print(json.dumps({'status': 'ok', 'summary': summary}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
