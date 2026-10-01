#!/usr/bin/env python3
"""Sweep approved Pacemaker log members with production sanitization."""

import argparse
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from sos.cleaner.corosync import CorosyncLogError, PacemakerLog
from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.extractor import SafeReportExtractor
from sos.cleaner.sanitizer import ReportSanitizer
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer


def archive_members(archive_path):
    with tarfile.open(archive_path, 'r:*') as archive:
        return [(member.name, member.size) for member in archive
                if member.isfile() and PacemakerLog.is_path(
                    tuple(member.name.split('/')))]


def run(archive_path, workdir):
    archive_path = os.path.abspath(archive_path)
    listed = sorted(archive_members(archive_path))
    extractor = SafeReportExtractor(archive_path, temp_parent=workdir)
    extracted = extractor.extract()
    session_workdir = os.path.join(workdir, 'session')
    os.mkdir(session_workdir, 0o700)
    try:
        root = ReportSanitizer._select_report_root(extracted)
        session = SanitizationSession(session_workdir)
        ReportIdentityDiscovery(root, session).discover()
        tree = ReportTreeSanitizer(root, os.path.join(workdir, 'unused'),
                                   session)
        mapping_started = time.perf_counter()
        tree._stabilize_mappings()
        mapping_seconds = time.perf_counter() - mapping_started
        session.freeze_mappings()
        tree._prepare_corosync_residual_check()
        sweep_started = time.perf_counter()
        members = []
        for relative, _size in listed:
            # The selected report root is the first archive component.
            path = Path(root) / '/'.join(relative.split('/')[1:])
            compressed_size = path.stat().st_size
            decoded_size = [None]
            started = time.perf_counter()
            try:
                with open(path, 'rb') as source:
                    PacemakerLog.sanitize(
                        source, compressed_size, session,
                        on_decoded=lambda size: decoded_size.__setitem__(0,
                                                                         size),
                        residual_check=lambda payload, rel=tuple(
                            relative.split('/')[1:]):
                        tree._check_corosync_output_residual(payload, rel))
            except CorosyncLogError as error:
                return {
                    'status': 'failure',
                    'members_total': len(listed),
                    'members_passed': len(members),
                    'members_failed': 1,
                    'compressed_bytes': sum(size for _name, size in listed),
                    'safe_path': '/'.join(error.relative_path or
                                          tuple(relative.split('/')[1:])),
                    'compressed_size': compressed_size,
                    'decompressed_size': decoded_size[0],
                    'category': error.category or 'unspecified',
                    'elapsed_seconds': time.perf_counter() - started,
                    'mapping_stabilization_seconds': mapping_seconds,
                    'transformation_seconds': time.perf_counter() - sweep_started,
                }
            members.append({
                'safe_path': relative.split('/', 1)[-1],
                'compressed_size': compressed_size,
                'decompressed_size': decoded_size[0],
                'elapsed_seconds': time.perf_counter() - started,
            })
        return {
            'status': 'pass',
            'members_total': len(listed),
            'members_passed': len(members),
            'members_failed': 0,
            'compressed_bytes': sum(size for _name, size in listed),
            'decompressed_bytes': sum(item['decompressed_size'] or 0
                                      for item in members),
            'elapsed_seconds': time.perf_counter() - sweep_started,
            'mapping_stabilization_seconds': mapping_seconds,
            'transformation_seconds': time.perf_counter() - sweep_started,
        }
    finally:
        shutil.rmtree(extracted, ignore_errors=True)
        shutil.rmtree(session_workdir, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', required=True)
    parser.add_argument('--result')
    args = parser.parse_args(argv)
    workdir = tempfile.mkdtemp(prefix='phase28-pacemaker-', dir='/var/tmp')
    os.chmod(workdir, 0o700)
    try:
        result = run(args.archive, workdir)
        rendered = json.dumps(result, sort_keys=True)
        print(rendered)
        if args.result:
            safe_result = {
                key: result[key] for key in (
                    'members_total', 'members_passed', 'members_failed',
                    'safe_path', 'category',
                    'mapping_stabilization_seconds',
                    'transformation_seconds') if key in result}
            with open(args.result, 'w', encoding='utf-8') as stream:
                os.chmod(args.result, 0o600)
                stream.write(json.dumps(safe_result, sort_keys=True) + '\n')
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
