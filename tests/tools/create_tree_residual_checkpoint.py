#!/usr/bin/env python3
"""Create a private, pre-residual-validation sanitizer checkpoint."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path

from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.extractor import SafeReportExtractor
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.sanitizer import ReportSanitizer
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer
from tests.tools.checkpoint_fingerprint import TREE_SCOPE, fingerprint
from tests.tools.run_tree_residual import git_head


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            fd = None
            json.dump(data, stream, sort_keys=True, indent=2)
            stream.write('\n')
    finally:
        if fd is not None:
            os.close(fd)


def create(source_archive, checkpoint, hostnames=(), domains=(), usernames=()):
    source_archive = os.path.abspath(source_archive)
    checkpoint = os.path.abspath(checkpoint)
    if os.path.lexists(checkpoint):
        raise ValueError('checkpoint already exists')
    os.mkdir(checkpoint, 0o700)
    extracted = None
    session_workdir = os.path.join(checkpoint, 'session-work')
    try:
        started = time.perf_counter()
        extractor = SafeReportExtractor(source_archive, temp_parent=checkpoint)
        extracted = extractor.extract()
        extraction = time.perf_counter() - started
        report_root = ReportSanitizer._select_report_root(extracted)

        session_started = time.perf_counter()
        os.mkdir(session_workdir, 0o700)
        session = SanitizationSession(
            session_workdir, hostnames=hostnames, domains=domains,
            usernames=usernames)
        ReportIdentityDiscovery(report_root, session).discover()
        tree = os.path.join(checkpoint, 'tree')
        os.mkdir(tree, 0o700)
        sanitizer = ReportTreeSanitizer(report_root, tree, session)
        sanitizer._stabilize_mappings()
        stabilization = time.perf_counter() - session_started
        session.freeze_mappings()
        manifest = SoSMappingManifest.from_session(session)

        tree_started = time.perf_counter()
        sanitizer._validate_roots()
        sanitizer._prepare_corosync_residual_check()
        sanitizer._staging_root = tree
        source_fd = sanitizer._open_directory(report_root, None, None)
        try:
            source_stat = os.fstat(source_fd)
            sanitizer._copy_directory(source_fd, tree, ())
        finally:
            os.close(source_fd)
        tree_fd = sanitizer._open_directory(tree, None, None)
        try:
            sanitizer._copy_stat(source_stat, destination_fd=tree_fd)
        finally:
            os.close(tree_fd)
        tree_sanitization = time.perf_counter() - tree_started

        _write_private(os.path.join(checkpoint, 'session-manifest.json'),
                       manifest.raw_mappings())
        metadata = {
            'checkpoint_version': 1,
            'source_archive': source_archive,
            'source_sha256': _sha256(source_archive),
            'git_head': git_head(),
            'fingerprint_scope': TREE_SCOPE,
            'fingerprint_sha256': fingerprint(
                Path(__file__).resolve().parents[2], TREE_SCOPE),
            'mapping_schema_version': SoSMappingManifest.schema_version,
            'mapping_frozen': True,
            'stage_timings_seconds': {
                'extraction': extraction,
                'mapping_stabilization': stabilization,
                'tree_sanitization': tree_sanitization,
            },
        }
        _write_private(os.path.join(checkpoint, 'checkpoint-metadata.json'),
                       metadata)
        os.chmod(checkpoint, 0o700)
        return metadata
    except Exception:
        if os.path.lexists(checkpoint):
            os.chmod(checkpoint, 0o700)
            shutil.rmtree(checkpoint)
        raise
    finally:
        if extracted is not None and os.path.lexists(extracted):
            shutil.rmtree(extracted)
        if os.path.lexists(session_workdir):
            shutil.rmtree(session_workdir)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-archive', required=True)
    parser.add_argument('--checkpoint', required=True)
    args = parser.parse_args(argv)
    metadata = create(args.source_archive, args.checkpoint)
    print(json.dumps({'status': 'created',
                      'stage_timings_seconds': metadata[
                          'stage_timings_seconds']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
