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
import logging
import os
import re
from datetime import datetime, timezone

log = logging.getLogger('sos')

# Snapshot filenames are ``baseline[-HOST][-NAME]-DATE[-ATTEMPT].json`` where
# DATE is written by save_snapshot() with this fixed shape (see date_str below)
# and ATTEMPT is the optional same-second collision suffix.
_SNAPSHOT_DATE_RE = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}Z'


def name_filter_regex(name):
    """Build a regex matching snapshot filenames with an exact NAME segment.

    A plain glob (``baseline-*-{name}-*.json``) is unsafe: ``*`` spans
    hyphens, so ``name`` matches as a loose substring -- ``web`` would match
    ``web-db`` and ``2026`` would match every snapshot via the timestamp.  We
    instead anchor NAME to the segment immediately before the fixed-shape DATE,
    and make the HOST segment optional so a snapshot saved with an empty
    hostname (``baseline-NAME-DATE.json``) still matches.

    ``name`` is regex-escaped, so this is also safe to call with an
    unvalidated value.  One residual ambiguity is inherent to the filename
    format: a name like ``db`` still matches a snapshot named ``web-db``,
    since ``db`` is a legitimate trailing segment; the delimiter (``-``) is
    valid inside both names and hostnames, so the two cannot be told apart
    from the filename alone.

    :param name: Baseline name to match exactly
    :type name: str

    :returns: Compiled regex to test against ``os.path.basename(path)``
    :rtype: re.Pattern
    """
    return re.compile(
        rf'^baseline-(?:.+-)?{re.escape(name)}-{_SNAPSHOT_DATE_RE}'
        rf'(?:-\d+)?\.json$')


def find_latest_snapshot(baseline_dir='/etc/sos/.baselines', name=''):
    """Find the most recent snapshot file.

    When ``name`` is empty, return the newest snapshot regardless of
    whether it is named or unnamed. The hostname embedded ineach
    filename is intentionally ignored so that the latest snapshot on
    this host is always selected.

    When ``name`` is given, only snapshots whose name segment matches
    exactly are considered (see :func:`name_filter_regex`).

    :param baseline_dir: Directory to scan for snapshots
    :type baseline_dir: str

    :param name: Optional baseline name to filter snapshots
    :type name: str

    :returns: Path to the newest snaphsot or None if none found
    :rtype: str or None
    """
    files = glob.glob(os.path.join(baseline_dir, 'baseline-*.json'))
    if name:
        name_re = name_filter_regex(name)
        files = [f for f in files if name_re.match(os.path.basename(f))]
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def load_snapshot(path):
    """Load and parse an snapshot JSON file.

    :param path: Path to the snapshot JSON file
    :type path: str

    :returns: Parsed snapshot data dict or None on error
    :rtype: dict or None
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.error(f"Failed to load snapshot '{path}' : {e}")
        return None


def save_snapshot(manifest_json, name='', hostname='',
                  baseline_dir='/etc/sos/.baselines'):
    """Save manifest JSON as a dated snapshot.

    Writes to: ``baseline-HOSTNAME[-NAME]-YYYY-MM-DD_HH-MM-SSZ.json``
    Permissions: ``0o400`` (owner read-only) after write.
    Directory: created with ``0o700`` if missing; a warning is logged
    if a pre-existing directory is group- or world-accessible.

    :param manifest_json: Manifest JSON string to write
    :type manifest_json: str

    :param name: Optional baseline name (alphanumerics, dots, hyphens,
        underscores only)
    :type name: str

    :param hostname: Hostname to embed in the snapshot filename
    :type hostname: str

    :param baseline_dir: Directory to write snapshot to
    :type baseline_dir: str

    :returns: Path to the saved snapshot or None on failure
    :rtype: str or None
    """
    if name and not re.match(r'^[a-zA-Z0-9._-]+$', name):
        log.error(f"Invalid baseline '{name}': "
                  "only alphanumerics, dots, hyphens, "
                  "and underscores are allowed")
        return None

    date_str = datetime.now(timezone.utc).strftime(
        '%Y-%m-%d_%H-%M-%SZ')
    host_part = f"-{hostname}" if hostname else ''
    name_part = f"-{name}" if name else ''
    base_name = f"baseline{host_part}{name_part}-{date_str}"
    # Assigned up-front so the error handlers below always have a path
    # to report, even if makedirs() fails before the retry loop.
    baseline_path = os.path.join(baseline_dir, f"{base_name}.json")

    try:
        os.makedirs(baseline_dir, mode=0o700, exist_ok=True)
        # ``makedirs`` only applies ``mode`` when itcreates the
        # directory; a pre-existing directory keeps its permissions.
        # Snapshots contain sensitive host inventory data, so warn the
        # admin if the directory is group- or world-accessible rather
        # than silently altering permissions they may have set on
        # purpose.
        # TODO: Decide if we want to change this automaticaly
        dir_mode = os.stat(baseline_dir).st_mode & 0o777
        if dir_mode & 0o077:
            log.warning(
                f"Baseline directory {baseline_dir} has permissions "
                f"{dir_mode:04o}; snapshots contain sensitive host "
                "inventory data and should be readable only by their "
                "owner (0700)")

        # The timestamp hasa 1-second resolution and no uniquifier, so
        # two runs in the same UTC second would collide on O_EXCL.
        # Retry with a numeric suffix so a same-second run still
        # persists rather than silently failing.
        attempt = 0
        while True:
            suffix = '' if attempt == 0 else f'-{attempt}'
            baseline_path = os.path.join(
                baseline_dir, f"{base_name}{suffix}.json")
            try:
                fd = os.open(
                    baseline_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                break
            except FileExistsError:
                attempt += 1
                if attempt > 100:
                    raise
        try:
            fp = os.fdopen(fd, 'w', encoding='utf-8')
        except Exception:
            os.close(fd)
            raise
        with fp:
            fp.write(manifest_json)

        # The snapshot is fully written at this point, so a chmod failure
        # should not mark the whole save as failed (which would leave a
        # valid file behind that find_latest_snapshot() still selects).
        # Warn and continue rather than falling through to the OSError
        # handler below
        try:
            os.chmod(baseline_path, 0o400)
        except OSError as e:
            log.warning("Snapshot saved but could not set read-only "
                        f"permissions on {baseline_path}: {e}")

        log.info(f"Snapshot saved to {baseline_path}")

        # TODO: snapshots currently accumulate indefinitely under
        # baseline_dir (default /etc/sos/.baselines), which can slowly
        # fill a small /etc partition.  Add retention/rotation here after
        # a successful save, so we keep the N most recent snapshots and/or
        # prune by age, ideally via a configurable tunable with a tested
        # default.
        return baseline_path
    except PermissionError as e:
        log.error("Permission denied writing snapshot to "
                  f"{baseline_path}: {e}")
    except OSError as e:
        log.error(
            f"Failed to save snapshot to {baseline_path}: {e}"
        )
    except Exception as e:
        log.error(f"Unexpected error saving snapshot: {e}")
    return None

# vim: set et ts=4 sw=4 :
