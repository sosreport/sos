# This file is part of the sos project: https://github.com/sosreport/sos

"""Fail-closed residual checks for a staged sanitized report tree."""

import errno
import os
import re
import socket
import stat

from sos.cleaner.text_residual import _has_residual, _packed


_NAMESPACES = ('hostnames', 'domains', 'ipv4', 'ipv6', 'mac',
               'emails', 'usernames')


def build_manifest_patterns(mappings):
    """Build detached known-original patterns for residual validation."""
    patterns = {}
    for namespace in _NAMESPACES:
        values = []
        for original, alias in mappings[namespace].items():
            if original == alias or original == '':
                continue
            if namespace == 'mac':
                pieces = original.replace('-', ':').split(':')
                expression = r'[:-]?'.join(re.escape(piece)
                                          for piece in pieces)
            else:
                expression = re.escape(original)
            if namespace in ('hostnames', 'domains'):
                expression = (r'(?<![A-Za-z0-9_-])' + expression +
                              r'(?![A-Za-z0-9_-])')
            elif namespace == 'username':
                expression = (r'(?<![A-Za-z0-9_.-])' + expression +
                              r'(?![A-Za-z0-9_.-])')
            elif namespace == 'email':
                expression = (r'(?<![\w@.-])' + expression +
                              r'(?![\w@-])')
            else:
                expression = (r'(?<![A-Za-z0-9_.:-])' + expression +
                              r'(?![A-Za-z0-9_.:-])')
            values.append((original, re.compile(
                expression, re.I if namespace in
                ('hostnames', 'domains', 'emails', 'mac') else 0)))
        patterns[namespace] = tuple(values)
    return patterns


class ResidualMatcher:
    """Immutable known-original matcher for one detached manifest.

    Each namespace retains the exact boundary expression used by the previous
    individual-pattern implementation.  The alternatives are compiled once,
    so validation does not repeatedly walk every mapping for every line.
    """

    def __init__(self, mappings):
        self.patterns = build_manifest_patterns(mappings)
        expressions = []
        for namespace, values in self.patterns.items():
            for _original, pattern in values:
                expression = pattern.pattern
                if namespace in ('hostnames', 'domains', 'emails', 'mac'):
                    expression = '(?i:' + expression + ')'
                expressions.append(expression)
        self._combined = re.compile('|'.join(expressions) or r'(?!)')

    def search(self, text):
        return self._combined.search(text) is not None


def known_original_residual(text, patterns):
    """Return whether a detached known-original pattern occurs in text."""
    if isinstance(patterns, ResidualMatcher):
        return patterns.search(text)
    return any(pattern.search(text) for values in patterns.values()
               for _original, pattern in values)


class ReportTreeResidualError(Exception):
    """A residual validation failure with a counts-only summary."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('report tree residual validation failed')


class ReportTreeResidualValidator:
    """Validate a fully staged tree without following links."""

    _namespaces = _NAMESPACES

    def __init__(self, staged, manifest):
        self.staged = os.path.abspath(staged)
        self.manifest = manifest
        self._summary = {
            'objects_checked': 0,
            'text_files_checked': 0,
            'symlinks_checked': 0,
            'residual_failures': 0,
        }
        raw = manifest.raw_mappings()
        self._patterns = ResidualMatcher(raw)
        self._ipv4_aliases = {
            _packed(alias, socket.AF_INET)
            for original, alias in raw['ipv4'].items()
            if original != alias
        }
        self._ipv6_aliases = {
            _packed(alias, socket.AF_INET6)
            for original, alias in raw['ipv6'].items()
            if original != alias
        }

    @staticmethod
    def _aliases(mapping):
        return tuple(alias for original, alias in mapping.items()
                     if original != alias)

    @classmethod
    def _build_patterns(cls, mappings):
        return build_manifest_patterns(mappings)

    def summary(self):
        return dict(self._summary)

    def validate(self):
        if not os.path.isdir(self.staged) or os.path.islink(self.staged):
            self._fail()
        try:
            self._scan_directory(self.staged)
        except ReportTreeResidualError:
            raise
        except Exception:
            self._fail()
        return dict(self._summary)

    def _fail(self):
        self._summary['residual_failures'] += 1
        raise ReportTreeResidualError(self._summary)

    def _known_residual(self, text):
        return known_original_residual(text, self._patterns)

    def _check_text(self, text):
        if self._known_residual(text):
            self._fail()
        # Reuse independent clean-text detectors. They only receive generated
        # IP aliases and never discover or mutate identities.
        if _has_residual(text, self._ipv4_aliases, self._ipv6_aliases):
            self._fail()

    @staticmethod
    def _open_text(path, observed):
        if not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd:
            raise OSError(errno.ENOTSUP, 'safe validation open unavailable')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            current = os.fstat(fd)
            if not stat.S_ISREG(current.st_mode) or \
                    (current.st_dev, current.st_ino) != \
                    (observed.st_dev, observed.st_ino):
                raise OSError(errno.EAGAIN, 'validated object changed')
            return fd
        except Exception:
            os.close(fd)
            raise

    def _scan_text_file(self, path, observed):
        fd = self._open_text(path, observed)
        try:
            with os.fdopen(fd, 'rb', closefd=True) as stream:
                for raw_line in stream:
                    if b'\0' in raw_line:
                        self._fail()
                    self._check_text(raw_line.decode('utf-8'))
        except ReportTreeResidualError:
            raise
        except (OSError, UnicodeError):
            self._fail()
        self._summary['text_files_checked'] += 1

    def _scan_directory(self, directory):
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except Exception:
            self._fail()
        for entry in entries:
            try:
                observed = entry.stat(follow_symlinks=False)
                kind = stat.S_IFMT(observed.st_mode)
                if kind == stat.S_IFLNK:
                    self._check_text(entry.name)
                    target = os.readlink(entry.path)
                    self._check_text(target)
                    self._summary['symlinks_checked'] += 1
                elif kind == stat.S_IFDIR:
                    if os.path.islink(entry.path):
                        self._fail()
                    self._check_text(entry.name)
                    self._scan_directory(entry.path)
                elif kind == stat.S_IFREG:
                    self._check_text(entry.name)
                    self._scan_text_file(entry.path, observed)
                else:
                    self._fail()
                self._summary['objects_checked'] += 1
            except ReportTreeResidualError:
                raise
            except Exception:
                self._fail()
