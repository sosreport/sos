# Copyright (C) 2026 Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging

from sos.report.snapshot.store import (
    find_latest_snapshot, load_snapshot
)
from sos.report.snapshot.incremental.metadata import (
    file_changed, collect_file_metadata, extract_files_metadata
)


class IncrementalTracker:
    """Consolidates snapshot loading, change detection, and
    incremental collection into a single entry point consumed
    by Report.
    """

    def __init__(self):
        """Initialize the incremental tracker."""
        self._previous = {}
        self._previous_path = None
        self.soslog = logging.getLogger('sos')

    def load_previous(self, name=''):
        """Find and load the latest snapshot, index by source_path.

        We use find_latest_snapshot() to locate the most recent
        snapshot file, load_snapshot() to parse it, and
        extract_files_metadata() to build a dict keyed by
        source_path for fast lookups during collection.

        :param name: Optional baseline name to filter snapshots
        :type name: str
        """
        prev = find_latest_snapshot(name=name)
        if prev:
            prev_data = load_snapshot(prev)
            if prev_data is None:
                self.soslog.warning(
                    f"Could not parse previous snapshot '{prev}'"
                    ", collecting all files."
                )
                return
            self._previous_path = prev
            self._previous = extract_files_metadata(prev_data)
            self.soslog.info(
                f"Loaded previous snapshot ({len(self._previous)}"
                f" files) for incremental collection."
            )
        else:
            self.soslog.warning(
                "No previous snapshot found, collecting all "
                "files."
            )

    def should_skip(self, path, file_stat):
        """Return True if file is unchanged vs previous snapshot.

        Looks up path in the indexed previous snapshot. If not
        found, returns False (new file, should be collected).
        If found, delegates to file_changed() and returns the
        inverse.

        :param path: The filesystem path to check
        :type path: str

        :param file_stat: Current stat result for the file
        :type file_stat: os.stat_result

        :returns: True if file is unchanged and should be skipped
        :rtype: bool
        """
        prev_meta = self._previous.get(path)
        if not prev_meta:
            return False
        return not file_changed(path, file_stat, prev_meta)

    def get_skip_metadata(self, path, file_stat):
        """Return metadata dict tagged as skipped_unchanged.

        Calls collect_file_metadata() and adds
        'collection_mode': 'skipped_unchanged' to indicate the
        file was not re-collected because it was unchanged.

        :param path: The filesystem path
        :type path: str

        :param file_stat: Current stat result for the file
        :type file_stat: os.stat_result

        :returns: Dictionary of file metadata with
            collection_mode set
        :rtype: dict
        """
        prev_meta = self._previous.get(path) or {}
        meta = collect_file_metadata(path, file_stat,
                                     known_hash=prev_meta.get('sha256'))
        if meta is not None:
            meta['collection_mode'] = 'skipped_unchanged'
        return meta

    @property
    def previous_snapshot_path(self):
        """Path to the loaded previous snapshot file,or None.

        Used by SoSReport.final_work() to include the previous
        snapshot in the archive.

        :returns: Absolute path to the previous snapshot or None
        :rtype: str or None
        """
        return self._previous_path

# vim: set et ts=4 sw=4 :
