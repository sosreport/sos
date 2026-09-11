# This file is part of the sos project: https://github.com/sosreport/sos

"""End-to-end orchestration for sanitizing a sosreport archive."""

import os
import shutil
import tempfile

from sos.cleaner.archiver import SafeReportArchiver
from sos.cleaner.archive_residual import ReportArchiveResidualValidator
from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.extractor import SafeReportExtractor
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.mapping_writer import MappingManifestWriter
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer


class ReportSanitizerError(Exception):
    """A fail-closed orchestration error with counts-only state."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('report sanitization failed')


class ReportSanitizer:
    """Run the private extraction, sanitization, validation, and archive flow."""

    def __init__(self, hostnames=(), domains=(), usernames=(),
                 temp_parent=None):
        self.hostnames = tuple(hostnames)
        self.domains = tuple(domains)
        self.usernames = tuple(usernames)
        self.temp_parent = temp_parent
        self._summary = {
            'discovered': {},
            'tree': {},
            'archive': {},
            'mapping_written': False,
            'mapping_entries': {},
        }

    def summary(self):
        return {
            'discovered': dict(self._summary['discovered']),
            'tree': dict(self._summary['tree']),
            'archive': dict(self._summary['archive']),
            'mapping_written': self._summary['mapping_written'],
            'mapping_entries': dict(self._summary['mapping_entries']),
        }

    def sanitize(self, input_archive, output_archive, mapping_output=None):
        input_archive = os.path.abspath(input_archive)
        output_archive = os.path.abspath(output_archive)
        if mapping_output is not None:
            mapping_output = os.path.abspath(mapping_output)
        workspace = None
        extracted = None
        sanitized_tree = None
        published_archive = False
        published_mapping = False
        archiver = None
        try:
            self._validate_arguments(input_archive, output_archive,
                                     mapping_output)
            workspace = tempfile.mkdtemp(prefix='.sos-report-sanitize-',
                                         dir=self.temp_parent)
            os.chmod(workspace, 0o700)
            if self._inside(output_archive, workspace):
                self._fail()
            if mapping_output is not None and self._inside(mapping_output,
                                                            workspace):
                self._fail()

            session_workdir = os.path.join(workspace, 'session')
            os.mkdir(session_workdir, 0o700)
            session = SanitizationSession(
                session_workdir, hostnames=self.hostnames,
                domains=self.domains, usernames=self.usernames)

            extracted = SafeReportExtractor(
                input_archive, temp_parent=workspace).extract()
            report_root = self._select_report_root(extracted)
            self._summary['discovered'] = ReportIdentityDiscovery(
                report_root, session).discover()
            # This is an in-memory snapshot only. It establishes the
            # post-discovery correlation state without exposing raw values.
            SoSMappingManifest.from_session(session)

            sanitized_tree = os.path.join(workspace, 'sanitized-tree')
            tree_destination = sanitized_tree
            self._summary['tree'] = ReportTreeSanitizer(
                extracted, tree_destination, session).sanitize()
            self._cleanup_path(extracted)
            extracted = None

            # Content sanitization can register ordinary email identities.
            # Snapshot the same session after tree sanitization for the
            # counts-only result; the tree sanitizer already performed the
            # residual gate with this same session before publishing.
            manifest = SoSMappingManifest.from_session(session)
            self._summary['discovered'] = manifest.summary()
            archiver = SafeReportArchiver(tree_destination, output_archive)
            archiver.create_private()
            ReportArchiveResidualValidator(
                archiver.private_path, manifest).validate()
            archiver.publish_private()
            self._summary['archive'] = archiver.summary()
            published_archive = True
            if mapping_output is not None:
                writer = MappingManifestWriter(manifest, mapping_output)
                writer.write()
                self._summary.update(writer.summary())
                published_mapping = True
            return self.summary()
        except ReportSanitizerError:
            raise
        except KeyboardInterrupt:
            if published_archive:
                self._remove_created(output_archive)
            if published_mapping:
                self._remove_created(mapping_output)
            raise
        except Exception:
            if published_archive and mapping_output is not None and \
                    not published_mapping:
                self._remove_created(output_archive)
            self._fail()
        finally:
            if archiver is not None and archiver.private_path is not None:
                archiver.discard_private()
            cleanup_error = False
            for path in (extracted, sanitized_tree, workspace):
                if path is None or not os.path.lexists(path):
                    continue
                try:
                    self._cleanup_path(path)
                except Exception:
                    cleanup_error = True
            if cleanup_error:
                if published_archive:
                    self._remove_created(output_archive)
                if published_mapping:
                    self._remove_created(mapping_output)
                self._fail()

    @staticmethod
    def _inside(path, root):
        try:
            return os.path.commonpath((os.path.realpath(path),
                                       os.path.realpath(root))) == \
                os.path.realpath(root)
        except ValueError:
            return False

    @staticmethod
    def _select_report_root(extracted):
        """Select the sole normal sosreport directory from extraction output."""
        try:
            entries = list(os.scandir(extracted))
            directories = [entry for entry in entries
                           if entry.is_dir(follow_symlinks=False)]
            if len(entries) != 1 or len(directories) != 1:
                raise ValueError
            return os.path.join(extracted, directories[0].name)
        except Exception:
            raise ReportSanitizerError({}) from None

    def _validate_arguments(self, input_archive, output_archive,
                            mapping_output=None):
        paths = [input_archive, output_archive]
        if mapping_output is not None:
            paths.append(mapping_output)
        real_paths = [os.path.realpath(path) for path in paths]
        if len(set(real_paths)) != len(real_paths):
            self._fail()
        if not os.path.isfile(input_archive) or os.path.islink(input_archive):
            self._fail()
        if not os.path.isdir(os.path.dirname(output_archive)):
            self._fail()
        if os.path.lexists(output_archive):
            self._fail()
        if mapping_output is not None:
            if (not os.path.isdir(os.path.dirname(mapping_output)) or
                    os.path.lexists(mapping_output)):
                self._fail()

    @staticmethod
    def _cleanup_path(path):
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)

    @staticmethod
    def _remove_created(path):
        if path is None:
            return
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
        except OSError:
            pass

    def _fail(self):
        raise ReportSanitizerError(self.summary())
