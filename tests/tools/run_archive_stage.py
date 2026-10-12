"""Run archive-stage validation from an already materialized tree checkpoint."""

import os
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path

from sos.cleaner.archiver import SafeReportArchiver
from sos.cleaner.mapping_writer import MappingManifestWriter
from sos.cleaner.filesystem import remove_private_tree
from sos.cleaner.session import SanitizationSession
from tests.tools.run_tree_residual import _private_manifest, validate_checkpoint


def report_root_name(source_archive):
    """Return the sole top-level directory selected by production semantics."""
    top = set()
    root_dirs = set()
    with tarfile.open(source_archive, mode='r:*') as archive:
        for member in archive:
            parts = member.name.split('/')
            if not parts or not parts[0] or parts[0] in ('.', '..'):
                raise ValueError('unsafe report root')
            top.add(parts[0])
            if len(parts) == 1 and member.isdir():
                root_dirs.add(parts[0])
    if len(top) != 1 or root_dirs != top:
        raise ValueError('ambiguous report root')
    return next(iter(top))


def sanitized_report_root_name(source_archive, manifest):
    """Apply production's frozen structural-name mapping to report_root_name."""
    root_name = report_root_name(source_archive)
    with tempfile.TemporaryDirectory(prefix='.sos-root-name-') as workdir:
        session = SanitizationSession(workdir)
        mapping = session.hostname_parser.mapping
        for original, alias in manifest.raw_mappings()['hostnames'].items():
            mapping.insert_to_dataset(original, alias)
            mapping.hosts[original.lower()] = alias
            mapping.add_regex_item(original)
        mapping.generate_compiled_regexes()
        return session.sanitize_known_text(root_name)


def archive_checkpoint(checkpoint, source_archive, archive, mapping_output):
    """Archive checkpoint contents with the production report-root boundary."""
    tree, manifest_path = validate_checkpoint(checkpoint)
    manifest = _private_manifest(manifest_path)
    root_name = sanitized_report_root_name(source_archive, manifest)
    workspace = tempfile.mkdtemp(prefix='.sos-archive-stage-',
                                  dir=os.path.dirname(os.path.abspath(archive)))
    os.chmod(workspace, 0o700)
    try:
        wrapped = os.path.join(workspace, root_name)
        # Hard-link regular files so the validated checkpoint is reused
        # without a second tree sanitization or a content copy.
        shutil.copytree(tree, wrapped, symlinks=True, copy_function=os.link)
        # Production archives the parent containing the selected report root,
        # so the root directory itself becomes the first archive member.
        result = SafeReportArchiver(workspace, archive).create()
        MappingManifestWriter(manifest, mapping_output).write()
        return result
    finally:
        if os.path.lexists(workspace):
            remove_private_tree(workspace)
