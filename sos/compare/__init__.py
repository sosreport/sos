# Copyright (C) 2026 Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import json
import os
import re

from sos.component import SoSComponent
from sos.report.snapshot.comparison import (compare_snapshots,
                                            format_diff_text,
                                            format_table)
from sos.report.snapshot.incremental.metadata import dict_at
from sos.report.snapshot.store import name_filter_regex


class SoSCompare(SoSComponent):

    desc = "Compare baseline snapshots for system diff detection"
    load_probe = False

    arg_defaults = {
        'action': '',
        'identifiers': [],
        'name': '',
        'baseline_dir': '/etc/sos/.baselines',
        'output_format': 'text',
        'profiles': [],
        'include': [],
        'exclude': [],
    }

    @classmethod
    def add_parser_options(cls, parser):
        parser.add_argument('action', nargs='?', default=None,
                            help="'list' or 'diff' (default: diff when "
                                 "identifiers are given, else list)")
        parser.add_argument('identifiers', nargs='*', default=[],
                            help="baseline dates, names, or paths "
                                 "(2 or more for diff)")
        parser.add_argument('--name', default='',
                            help='filter by baseline name')
        parser.add_argument('--baseline-dir', default='/etc/sos/.baselines',
                            dest='baseline_dir',
                            help='directory holding baseline snapshots '
                                 '(default: /etc/sos/.baselines)')
        parser.add_argument('--output-format',
                            choices=['text', 'json'], default='text',
                            dest='output_format',
                            help='output format (default: text)')
        parser.add_argument('-p', '--profile', '--profiles',
                            action='extend', dest='profiles', type=str,
                            default=[],
                            help='only compare files from plugins '
                                 'belonging to these profiles')
        parser.add_argument('-i', '--include',
                            action='extend', dest='include', type=str,
                            default=[],
                            help='only include paths matching these '
                                 'glob patterns (e.g. "/etc/*")')
        parser.add_argument('-e', '--exclude',
                            action='extend', dest='exclude', type=str,
                            default=[],
                            help='exclude paths matching these '
                                 'glob patterns (e.g. "/proc/*")')

    def execute(self):
        if self.opts.name and not re.match(r'^[a-zA-Z0-9._-]+$',
                                           self.opts.name):
            self.ui_log.error(
                f"Invalid --name '{self.opts.name}': only alphanumerics, "
                "dots, hyphens, and underscores are allowed")
            return
        action = self.opts.action
        ids = list(self.opts.identifiers)
        # 'action' here is optional. If the first token is an explicit
        # keyword, use it (keeps 'sos compare diff a b' working);
        # otherwise treat every token as an identifier and default to diff,
        # so 'sos diff a b' and 'sos compare a b' work without repeating
        # the word. We may want to rework this if we don't like the
        # compare keyword
        if action not in ('list', 'diff'):
            if action:
                ids.insert(0, action)
            action = 'diff' if ids else 'list'
        self.opts.identifiers = ids
        try:
            if action == 'list':
                self._do_list()
            elif action == 'diff':
                self._do_diff()
        finally:
            self.cleanup()

    @staticmethod
    def _get_snapshot_info(data):
        """Extract system and snapshot info from a manifest dict"""
        snap_info = dict_at(data, 'components', 'report', 'snapshot')
        system = dict_at(snap_info, 'system')
        return {
            'hostname': system.get('hostname', ''),
            'kernel': system.get('kernel', ''),
            'arch': system.get('arch', ''),
            'collection_type': snap_info.get('collection_type', ''),
        }

    def _read_json(self, path):
        """Load and parse a JSON file, logging errors on failure"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.ui_log.error(
                f"Failed to load baseline '{path}': {e}")
            return None
        if not isinstance(data, dict):
            self.ui_log.error(
                f"Baseline '{path}' is not a valid snapshot "
                "(expected a JSON object)")
            return None
        return data

    def _load_baseline(self, identifier):
        """Load a baseline JSON fileby date, name, or full path"""
        baseline_dir = self.opts.baseline_dir
        real_base = os.path.realpath(baseline_dir)

        # Full path provided, so only accept path-like identifiers
        if os.sep in identifier or identifier.startswith(os.sep):
            if not os.path.isfile(identifier):
                self.ui_log.error(
                    f"No baseline found at path '{identifier}'")
                self._list_available()
                return None
            real_path = os.path.realpath(identifier)
            if not real_path.startswith(real_base + os.sep):
                self.ui_log.error(
                    f"Baseline path '{identifier}' is outside "
                    f"the baseline directory '{baseline_dir}'")
                return None
            return self._read_json(real_path)
        # Direct filename match! (with or without .json)
        for suffix in ('', '.json'):
            direct = os.path.join(baseline_dir, identifier + suffix)
            if os.path.isfile(direct):
                real_direct = os.path.realpath(direct)
                if not real_direct.startswith(real_base + os.sep):
                    continue
                return self._read_json(real_direct)
        # Glob match, since the hostname is embedded in the filename we
        # match around the identifier to find it.
        matches = glob.glob(
            os.path.join(baseline_dir,
                         f"baseline-*{glob.escape(identifier)}*.json"))
        if matches:
            matches.sort(key=os.path.getmtime, reverse=True)
            real_match = os.path.realpath(matches[0])
            if not real_match.startswith(real_base + os.sep):
                self.ui_log.error(
                    f"Baseline '{matches[0]}' resolves outside the "
                    f"baseline directory '{baseline_dir}'")
                return None
            return self._read_json(real_match)
        self.ui_log.error(f"No baseline found matching '{identifier}'")
        self._list_available()
        return None

    def _list_available(self, name=''):
        """Print available baselines in a formatted table.
        We could do a simple tab or space separated output
        if the table is too much."""
        baseline_dir = self.opts.baseline_dir
        files = glob.glob(os.path.join(baseline_dir, 'baseline-*.json'))
        if name:
            # Lets anchor name to an exact filename part rather than a
            # loose `baseline-*-{name}-*` glob (where `*` spans hyphens);
            # see store.name_filter_regex().
            name_re = name_filter_regex(name)
            files = [f for f in files if name_re.match(os.path.basename(f))]
        files = sorted(files, key=os.path.getmtime, reverse=True)
        if not files:
            self.ui_log.info("No baseline snapshots found.")
            return
        # This all refers to the json files, we may want to extend
        # this to the actual file location as well in another view
        # TODO: I think 'Size' and 'Location' may not be clear enough
        # so these headers may need to be renamed or more explicit.
        headers = ['Snapshot', 'Size', 'Location', 'Type']
        rows = []
        for baseline_path in files:
            size = os.path.getsize(baseline_path)
            fname = os.path.basename(baseline_path)
            data = self._read_json(baseline_path)
            ctype = ''
            if data:
                info = self._get_snapshot_info(data)
                ctype = info['collection_type']
            rows.append([fname, f'{size:,} B', baseline_path, ctype])
        self.ui_log.info(format_table(headers, rows))

    def _do_list(self):
        self._list_available(name=self.opts.name)

    def _do_diff(self):
        ids = self.opts.identifiers
        if len(ids) < 2:
            self.ui_log.error(
                "diff requires at least two identifiers: "
                "sos compare diff <id1> <id2> [<id3> ...]")
            return
        # Haven't managed to make more than 3 items pretty yet
        if len(ids) > 3 and self.opts.output_format == 'text':
            self.ui_log.error(
                f"Cannot compare {len(ids)} snapshots in text output: "
                "the table could exceed the terminal width (limit: 3). "
                "Use --output-format json to compare more, or pass 3 or "
                "fewer identifiers.")
            return
        snapshots = []
        labels = []
        for ident in ids:
            data = self._load_baseline(ident)
            if data is None:
                return
            snapshots.append(data)
            labels.append(ident)
        hostnames = set()
        for snap in snapshots:
            info = self._get_snapshot_info(snap)
            if info['hostname']:
                hostnames.add(info['hostname'])
        if len(hostnames) > 1:
            # Warning here, but this feature may be useful
            # when comparing cluster nodes or similar where
            # we expect certain files to be exactly the same
            self.ui_log.warning(
                "WARNING: comparing snapshots from different "
                f"hosts: {', '.join(sorted(hostnames))}")
        result = compare_snapshots(*snapshots, labels=labels,
                                   profiles=self.opts.profiles or None,
                                   include=self.opts.include or None,
                                   exclude=self.opts.exclude or None)
        if self.opts.output_format == 'json':
            self.ui_log.info(
                json.dumps(result, indent=4, default=str))
        else:
            self.ui_log.info(format_diff_text(result))

# vim: set et ts=4 sw=4 :
