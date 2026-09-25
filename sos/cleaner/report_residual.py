# This file is part of the sos project: https://github.com/sosreport/sos

"""Fail-closed residual checks for a staged sanitized report tree."""

import errno
import os
import re
import socket
import stat

from sos.cleaner.text_residual import _has_residual, _packed
from sos.cleaner.pacemaker import (PacemakerSchedulerInput,
                                   PacemakerSchedulerInputError)
from sos.cleaner.edid import DrmEdidPolicy
from sos.cleaner.corosync import (CorosyncLog, CorosyncLogError,
                                   PacemakerLog)
from sos.cleaner.sssd import SssdLog
from sos.cleaner.acpi import is_path as is_acpi_path
from sos.cleaner.systemd import is_path as is_systemd_coredump_path
from sos.cleaner.selinux_store import (active_store_module_path,
                                       active_store_path)
from sos.cleaner.selinux_cil import DirectCil, DirectCilError


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
        self._literal = _LiteralResidualMatcher()
        self._fallback = []
        self._non_ascii_fallback = False
        mac_expressions = []
        order = 0
        for namespace, values in self.patterns.items():
            for original, pattern in values:
                if namespace == 'mac' or not original.isascii():
                    self._fallback.append((namespace, original, pattern,
                                           order))
                    if namespace == 'mac':
                        expression = pattern.pattern
                        mac_expressions.append('(?i:' + expression + ')')
                    self._non_ascii_fallback |= not original.isascii()
                elif original.isascii():
                    self._literal.add(
                        # Scan one normalized trie.  Case-sensitive entries
                        # are verified against the original slice by
                        # _LiteralResidualMatcher.search().
                        original.lower(),
                        namespace, order, namespace in
                        ('hostnames', 'domains', 'emails'), original)
                order += 1
        self._literal.finish()
        self._fallback_anchors = frozenset(
            original[:2].lower() for _namespace, original, _pattern, _order
            in self._fallback if len(original) >= 2)
        self._mac_combined = re.compile('|'.join(mac_expressions) or r'(?!)')
        self._mac_order = next(
            (order for namespace, _original, _pattern, order in self._fallback
             if namespace == 'mac'), None)
        self._mac_candidate = re.compile(
            r'(?i)(?:[0-9a-f]{2}[-:_]?){6}')
        anchors = set()
        single_character_anchors = set()
        for namespace, values in self.patterns.items():
            for original, _pattern in values:
                # Every accepted match contains the first two literal
                # characters of its original (or its sole character). MAC
                # separators are optional, so do not include a separator in
                # this anchor.
                anchor = original[:2]
                if not anchor:
                    continue
                if len(anchor) == 1:
                    single_character_anchors.add(anchor.lower())
                else:
                    anchors.add(anchor.lower())
        self._anchors = frozenset(anchors)
        self._single_character_anchors = frozenset(single_character_anchors)

    def may_match(self, text):
        """Return whether the line may contain a known original.

        This is only a conservative dispatch filter.  The compiled residual
        matcher remains the sole source of the known-original decision.
        """
        if not self._anchors and not self._single_character_anchors:
            return False
        # ASCII lower-casing has the same case-insensitive behavior as the
        # namespace patterns for the identities accepted by the sanitizer.
        # Non-ASCII input takes the conservative path because Unicode case
        # folding has equivalences that are not safely represented by a
        # two-byte literal index.
        if not text.isascii():
            return True
        lowered = text.lower()
        if self._single_character_anchors and any(
                character in lowered
                for character in self._single_character_anchors):
            return True
        return any(lowered[index:index + 2] in self._anchors
                   for index in range(len(lowered) - 1))

    def search(self, text):
        return self.match_category(text) is not None

    def match_category(self, text):
        """Return the first matching namespace, preserving regex semantics."""
        if text.isascii():
            literal_match = self._literal.search(text)
            lowered = text.lower()
            if not any(anchor in lowered for anchor in
                       self._fallback_anchors):
                return literal_match[2] if literal_match else None
            fallback_matches = []
            for namespace, _original, pattern, _order in self._fallback:
                if namespace == 'mac':
                    continue
                match = pattern.search(text)
                if match is not None:
                    fallback_matches.append((match.start(), _order, namespace))
            match = (self._mac_combined.search(text)
                     if self._mac_candidate.search(text) else None)
            if match is not None:
                # The combined expression is in manifest order.  Its match
                # category is always MAC; order is resolved against the
                # literal/fallback candidates by the first MAC entry's
                # manifest order, which is sufficient because MAC entries
                # occupy one namespace block.
                fallback_matches.append((match.start(), self._mac_order,
                                         'mac'))
            if literal_match is None and not fallback_matches:
                return None
            candidates = fallback_matches + ([literal_match]
                                              if literal_match else [])
            return min(candidates, key=lambda value: (value[0], value[1]))[2]
        return self._combined_category(text)

    def _combined_category(self, text):
        """Use the reference regex path for non-ASCII edge semantics."""
        match = self._combined.search(text)
        if match is None:
            return None
        match_span = match.span()
        for namespace, values in self.patterns.items():
            for _original, pattern in values:
                candidate = pattern.search(text)
                if candidate is not None and candidate.span() == match_span:
                    return namespace
        return 'unknown'


class _LiteralResidualMatcher:
    """A small Aho-Corasick matcher for boundary-checked literals."""

    def __init__(self):
        self._nodes = [{'next': {}, 'fail': 0, 'outputs': []}]
        self._entries = []
        self._max_length = 0

    def add(self, literal, namespace, order, insensitive, original=None):
        node = 0
        for character in literal:
            node = self._nodes[node]['next'].setdefault(
                character, len(self._nodes))
            if node == len(self._nodes):
                self._nodes.append({'next': {}, 'fail': 0, 'outputs': []})
        entry = (literal, namespace, order, insensitive,
                 literal if original is None else original)
        index = len(self._entries)
        self._entries.append(entry)
        self._nodes[node]['outputs'].append(index)
        self._max_length = max(self._max_length, len(literal))

    def finish(self):
        queue = []
        for child in self._nodes[0]['next'].values():
            queue.append(child)
        while queue:
            node = queue.pop(0)
            for character, child in self._nodes[node]['next'].items():
                queue.append(child)
                fallback = self._nodes[node]['fail']
                while fallback and character not in self._nodes[fallback]['next']:
                    fallback = self._nodes[fallback]['fail']
                self._nodes[child]['fail'] = self._nodes[fallback]['next'].get(
                    character, 0)
                self._nodes[child]['outputs'].extend(
                    self._nodes[self._nodes[child]['fail']]['outputs'])

    @staticmethod
    def _boundary(namespace, text, start, end):
        if namespace in ('hostnames', 'domains'):
            forbidden_before = lambda c: c.isascii() and (
                c.isalnum() or c in '_-')
            forbidden_after = forbidden_before
        elif namespace == 'username':
            forbidden_before = lambda c: c.isascii() and (
                c.isalnum() or c in '_.-')
            forbidden_after = forbidden_before
        elif namespace == 'emails':
            forbidden_before = lambda c: c.isascii() and (
                c.isalnum() or c in '_@.-')
            forbidden_after = lambda c: c.isascii() and (
                c.isalnum() or c in '_@-')
        else:
            forbidden_before = lambda c: c.isascii() and (
                c.isalnum() or c in '_.:-')
            forbidden_after = forbidden_before
        return ((start == 0 or not forbidden_before(text[start - 1])) and
                (end == len(text) or not forbidden_after(text[end])))

    def search(self, text):
        if not self._entries:
            return None
        scan_text = text.lower() if text.isascii() else text
        node = 0
        matches = []
        for position, character in enumerate(scan_text):
            while node and character not in self._nodes[node]['next']:
                node = self._nodes[node]['fail']
            node = self._nodes[node]['next'].get(character, 0)
            for index in self._nodes[node]['outputs']:
                literal, namespace, order, _insensitive, original = \
                    self._entries[index]
                start = position - len(literal) + 1
                # The trie is scanned in lowercase for the case-insensitive
                # namespaces.  Username mappings are deliberately
                # case-sensitive; reject lowercase-trie hits that do not
                # match the original spelling before applying boundaries.
                if not _insensitive and text[start:position + 1] != original:
                    continue
                if self._boundary(namespace, text, start, position + 1):
                    matches.append((start, order, namespace))
        if not matches:
            return None
        best = min(matches, key=lambda value: (value[0], value[1]))
        return best[0], best[1], best[2]


def known_original_residual(text, patterns):
    """Return whether a detached known-original pattern occurs in text."""
    if isinstance(patterns, ResidualMatcher):
        return patterns.search(text)
    return any(pattern.search(text) for values in patterns.values()
               for _original, pattern in values)


class ReportTreeResidualError(Exception):
    """A residual validation failure with safe category/path metadata."""

    def __init__(self, summary, category=None, relative_path=None):
        self.summary = dict(summary)
        self.category = category
        self.relative_path = tuple(relative_path) if relative_path else None
        super().__init__('report tree residual validation failed')


class ReportTreeResidualValidator:
    """Validate a fully staged tree without following links."""

    _namespaces = _NAMESPACES
    _corosync_authkey_path = ('etc', 'corosync', 'authkey')
    _selinux_file_contexts_bin_paths = frozenset((
        ('etc', 'selinux', 'targeted', 'contexts', 'files',
         'file_contexts.bin'),
        ('etc', 'selinux', 'targeted', 'contexts', 'files',
         'file_contexts.homedirs.bin'),
    ))
    _selinux_binary_policy_versions = frozenset(str(version)
                                                 for version in range(15, 36))
    _process_environment_max_pid = 4194303
    _timezone_paths = frozenset((
        ('usr', 'share', 'zoneinfo', 'Etc', 'UTC'),
        ('usr', 'share', 'zoneinfo', 'Australia', 'Sydney'),
    ))

    @classmethod
    def _is_corosync_authkey_path(cls, relative):
        relative = tuple(relative)
        return relative == cls._corosync_authkey_path or (
            len(relative) == 4 and relative[1:] == cls._corosync_authkey_path)

    @classmethod
    def _is_selinux_file_contexts_bin_path(cls, relative):
        relative = tuple(relative)
        return relative in cls._selinux_file_contexts_bin_paths or any(
            len(relative) == len(target) + 1 and relative[1:] == target
            for target in cls._selinux_file_contexts_bin_paths)

    @classmethod
    def _is_selinux_binary_policy_path(cls, relative):
        relative = tuple(relative)
        for prefix in ((), (relative[0],) if relative else ()):
            candidate = relative[len(prefix):]
            if (candidate[:4] == ('etc', 'selinux', 'targeted', 'policy') and
                    len(candidate) == 5 and
                    candidate[4].startswith('policy.') and
                    candidate[4][7:] in cls._selinux_binary_policy_versions):
                return True
        return False

    @classmethod
    def _is_process_environment_path(cls, relative):
        relative = tuple(relative)
        if len(relative) == 3 and relative[0] == 'proc':
            parts = relative
        elif len(relative) == 4 and relative[1] == 'proc':
            parts = relative[1:]
        else:
            return False
        pid, filename = parts[1:]
        if (not pid or not pid.isascii() or not pid.isdecimal() or
                pid[0] == '0' or filename != 'environ'):
            return False
        return 1 <= int(pid) <= cls._process_environment_max_pid

    @classmethod
    def _is_selinux_active_store_omission_path(cls, relative):
        return ((active_store_module_path(relative) is not None and
                 not DirectCil.is_path(relative)) or
                any(active_store_path(relative, name) for name in (
                    'policy.kern', 'policy.linked', 'modules_checksum',
                    'commit_num')))

    @classmethod
    def _is_timezone_path(cls, relative):
        relative = tuple(relative)
        return relative in cls._timezone_paths or (
            len(relative) == 1 + len(next(iter(cls._timezone_paths))) and
            relative[1:] in cls._timezone_paths)

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
        self._corosync_members = 0
        self._corosync_bytes = 0

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

    def _fail(self, category=None, relative_path=None):
        self._summary['residual_failures'] += 1
        if isinstance(relative_path, (str, bytes, os.PathLike)):
            relative_path = os.path.relpath(relative_path, self.staged)
            relative_path = tuple(relative_path.split(os.sep))
        raise ReportTreeResidualError(self._summary, category, relative_path)

    def _accept_corosync_payload(self, size):
        if self._corosync_members >= CorosyncLog.MAX_MEMBERS or \
                self._corosync_bytes + size > CorosyncLog.MAX_AGGREGATE:
            self._fail()
        self._corosync_members += 1
        self._corosync_bytes += size

    def _known_residual(self, text):
        return known_original_residual(text, self._patterns)

    def _check_text(self, text, relative_path=None):
        category = self._patterns.match_category(text)
        if category is not None:
            self._fail('known ' + category.rstrip('s'), relative_path)
        # Reuse independent clean-text detectors. They only receive generated
        # IP aliases and never discover or mutate identities.
        if _has_residual(text, self._ipv4_aliases, self._ipv6_aliases):
            self._fail('generic residual', relative_path)

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
                    self._check_text(raw_line.decode('utf-8'), path)
        except ReportTreeResidualError:
            raise
        except (OSError, UnicodeError):
            self._fail()
        self._summary['text_files_checked'] += 1

    def _scan_scheduler_file(self, path, observed):
        fd = self._open_text(path, observed)
        try:
            with os.fdopen(fd, 'rb', closefd=True) as stream:
                payload = PacemakerSchedulerInput.decode(
                    stream, observed.st_size)
            PacemakerSchedulerInput.residual_check(payload)
            for raw_line in payload.splitlines(keepends=True):
                self._check_text(raw_line.decode('utf-8'), path)
        except ReportTreeResidualError:
            raise
        except (OSError, UnicodeError, PacemakerSchedulerInputError):
            self._fail('specialized-artifact residual', path)

    def _scan_corosync_file(self, path, observed):
        fd = self._open_text(path, observed)
        try:
            with os.fdopen(fd, 'rb', closefd=True) as stream:
                payload = CorosyncLog.decode(stream, observed.st_size)
            self._accept_corosync_payload(len(payload))
            for raw_line in payload.decode('utf-8').splitlines(
                    keepends=True):
                self._check_text(raw_line, path)
        except ReportTreeResidualError:
            raise
        except (OSError, UnicodeError, CorosyncLogError):
            self._fail('specialized-artifact residual', path)

    def _scan_pacemaker_file(self, path, observed):
        fd = self._open_text(path, observed)
        try:
            with os.fdopen(fd, 'rb', closefd=True) as stream:
                payload = PacemakerLog.decode(stream, observed.st_size)
            for raw_line in payload.decode('utf-8').splitlines(
                    keepends=True):
                self._check_text(raw_line, path)
        except ReportTreeResidualError:
            raise
        except (OSError, UnicodeError, CorosyncLogError):
            self._fail('specialized-artifact residual', path)

    def _scan_direct_cil_file(self, path, observed):
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            self._fail()
        fd = self._open_text(path, observed)
        try:
            with os.fdopen(fd, 'rb', closefd=True) as stream:
                payload = DirectCil.decode(stream, observed.st_size)
            DirectCil.residual_check(
                payload, lambda text: self._check_text(text, path))
        except ReportTreeResidualError:
            raise
        except (OSError, UnicodeError, DirectCilError):
            self._fail('specialized-artifact residual', path)

    def _scan_directory(self, directory, relative=()):
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except Exception:
            self._fail()
        for entry in entries:
            try:
                entry_relative = relative + (entry.name,)
                observed = entry.stat(follow_symlinks=False)
                if DirectCil.is_path(entry_relative):
                    self._scan_direct_cil_file(entry.path, observed)
                    self._summary['objects_checked'] += 1
                    continue
                if PacemakerSchedulerInput.is_path(entry_relative):
                    if not stat.S_ISREG(observed.st_mode) or \
                            observed.st_nlink != 1:
                        self._fail()
                    self._scan_scheduler_file(entry.path, observed)
                    self._summary['objects_checked'] += 1
                    continue
                if DrmEdidPolicy.is_path(entry_relative):
                    self._fail()
                if CorosyncLog.is_path(entry_relative):
                    if not stat.S_ISREG(observed.st_mode) or \
                            observed.st_nlink != 1:
                        self._fail()
                    self._scan_corosync_file(entry.path, observed)
                    self._summary['objects_checked'] += 1
                    continue
                if PacemakerLog.is_path(entry_relative):
                    if not stat.S_ISREG(observed.st_mode) or \
                            observed.st_nlink != 1:
                        self._fail()
                    self._scan_pacemaker_file(entry.path, observed)
                    self._summary['objects_checked'] += 1
                    continue
                if (self._is_corosync_authkey_path(entry_relative) or
                        self._is_selinux_file_contexts_bin_path(entry_relative) or
                        self._is_selinux_binary_policy_path(entry_relative) or
                        self._is_selinux_active_store_omission_path(
                            entry_relative) or
                        self._is_process_environment_path(entry_relative) or
                        SssdLog.is_path(entry_relative) or
                        is_acpi_path(entry_relative) or
                        is_systemd_coredump_path(entry_relative) or
                        self._is_timezone_path(entry_relative)):
                    self._fail()
                kind = stat.S_IFMT(observed.st_mode)
                if kind == stat.S_IFLNK:
                    self._check_text(entry.name, entry_relative)
                    target = os.readlink(entry.path)
                    self._check_text(target, entry_relative)
                    self._summary['symlinks_checked'] += 1
                elif kind == stat.S_IFDIR:
                    if os.path.islink(entry.path):
                        self._fail()
                    self._check_text(entry.name, entry_relative)
                    self._scan_directory(entry.path, entry_relative)
                elif kind == stat.S_IFREG:
                    self._check_text(entry.name, entry_relative)
                    self._scan_text_file(entry.path, observed)
                else:
                    self._fail()
                self._summary['objects_checked'] += 1
            except ReportTreeResidualError:
                raise
            except Exception:
                self._fail()
