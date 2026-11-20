# Copyright (C) 2026 Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.snapshot.incremental.metadata import extract_files_metadata


# Fields shown by "sos compare", but not the same set file_changed() uses:
# ctime is omitted here (too noisy for a diff until we work out options
# to use it) owner/group names andselinux_context are included.
COMPARE_FIELDS = ('file_type', 'link_target', 'mode', 'uid',
                  'gid', 'owner', 'group', 'size', 'mtime_ns',
                  'sha256', 'selinux_context')

# TODO: Wecan probably find a better value for this, or just add
# N/A
ABSENT = '-'


def _hline(widths, left, mid, right, fill='─'):
    return left + mid.join(fill * width for width in widths) + right


def _data_row(cells, widths):
    parts = []
    for cell, width in zip(cells, widths):
        parts.append(f' {cell:<{width - 1}}')
    return '│' + '│'.join(parts) + '│'


def _span_row(text, widths):
    inner = sum(widths) + len(widths) - 1
    text_str = str(text)
    max_len = inner - 2
    if len(text_str) > max_len:
        text_str = text_str[:max_len - 2] + '..'
    return '│' + f' {text_str:<{inner - 1}}' + '│'


def format_table(headers, rows, max_col=0):
    """Format rows as a box-drawn table with auto-sized columns.

    :param headers: Column header labels
    :type headers: list

    :param rows: Table rows, each a sequence of cell values
    :type rows: list

    :param max_col: Optional maximum column width (0 = unlimited)
    :type max_col: int

    :returns: The rendered multi-line table
    :rtype: str
    """
    num_columns = len(headers)
    widths = [len(header) + 2 for header in headers]
    for row in rows:
        for i in range(min(num_columns, len(row))):
            widths[i] = max(widths[i], len(str(row[i])) + 2)
    if max_col:
        widths = [min(width, max_col) for width in widths]

    def _trunc(text, width):
        text_str = str(text)
        if len(text_str) > width - 2:
            return text_str[:width - 4] + '..'
        return text_str

    lines = []
    lines.append(_hline(widths, '┌', '┬', '┐'))
    lines.append(_data_row(
        [_trunc(header, width) for header, width in zip(headers, widths)],
        widths))
    lines.append(_hline(widths, '├', '┼', '┤'))
    for row in rows:
        cells = [_trunc(row[i] if i < len(row) else '', widths[i])
                 for i in range(num_columns)]
        lines.append(_data_row(cells, widths))
    lines.append(_hline(widths, '└', '┴', '┘'))
    return '\n'.join(lines)


def compare_snapshots(*snapshot_data, labels=None, profiles=None,
                      include=None, exclude=None):
    """Compare N snapshot manifests side by side.

    Returns only files and fields that differ across at least
    one snapshot.  Files present in all snapshots with identical
    metadata are counted but omitted from the detail.

    :param snapshot_data: Two or more manifest dicts
    :type snapshot_data: dict

    :param labels:        Optional display labels (dates, names)
    :type labels: list or None

    :param profiles:      Optional list of profile names to filter by
    :type profiles: list or None

    :param include:       Optional glob patterns keeping only matching paths
    :type include: list or None

    :param exclude:       Optional glob patterns for paths to skip
    :type exclude: list or None

    :returns: Comparison result dict with labels, files, summary
    :rtype: dict

    :raises ValueError: If fewer than 2 snapshots are provided, or if
        the number of labels does not match the number of snapshots
    """
    # TODO: Work in making sure that comparing 3 snapshots is clear
    # enough
    if len(snapshot_data) < 2:
        raise ValueError("Need at least 2 snapshots to compare")

    num_snapshots = len(snapshot_data)
    if labels is not None and len(labels) != num_snapshots:
        raise ValueError(
            f"Got {len(labels)} label(s) for {num_snapshots} snapshot(s)")
    if labels is None:
        labels = [f"snap{i+1}" for i in range(num_snapshots)]

    all_files = [extract_files_metadata(s, profiles=profiles,
                                        include=include, exclude=exclude)
                 for s in snapshot_data]

    all_paths = set()
    for files in all_files:
        all_paths.update(files)

    changed = []
    unchanged_count = 0

    for path in sorted(all_paths):
        present = [path in files for files in all_files]

        if not all(present):
            fields = {'_status': [
                'present' if is_present else ABSENT
                for is_present in present
            ]}
            for field in COMPARE_FIELDS:
                vals = [all_files[i].get(path, {}).get(field)
                        for i in range(num_snapshots)]
                if any(val is not None for val in vals):
                    fields[field] = [
                        val if val is not None else ABSENT
                        for val in vals
                    ]
            changed.append({'path': path, 'fields': fields})
            continue

        diff_fields = {}
        for field in COMPARE_FIELDS:
            vals = [all_files[i][path].get(field)
                    for i in range(num_snapshots)]
            if any(val != vals[0] for val in vals[1:]):
                diff_fields[field] = [
                    val if val is not None else ABSENT
                    for val in vals
                ]

        if diff_fields:
            changed.append({'path': path, 'fields': diff_fields})
        else:
            unchanged_count += 1

    return {
        'labels': labels,
        'files': changed,
        'summary': {
            'total_files': len(all_paths),
            'changed_files': len(changed),
            'unchanged_files': unchanged_count,
        }
    }


def _shorten_label(label, max_len):
    """Shorten a baseline label to fit a column width.

    Strips the 'baseline-' prefix first, then the hostname
    segment if still too long, keeping the name and timestamp
    which are the distinguishing parts.
    """
    # TODO: This feels a bit clumsy, and I may be missing
    # data by doing this, so this needs to be tested thoroughly.
    short_label = str(label)
    if len(short_label) <= max_len:
        return short_label
    if short_label.startswith('baseline-'):
        short_label = short_label[len('baseline-'):]
    if len(short_label) <= max_len:
        return short_label
    # baseline filenames are HOSTNAME-NAME-TIMESTAMP or
    # HOSTNAME-TIMESTAMP, so drop hostname to keep the tail
    parts = short_label.split('-')
    # find where the date starts (YYYY-MM-DD pattern)
    for i, part in enumerate(parts):
        if len(part) == 4 and part.isdigit() and i > 0:
            tail = '-'.join(parts[i:])
            # include the part just before the date (the name)
            if i >= 2:
                tail = parts[i - 1] + '-' + tail
            if len(tail) <= max_len:
                return tail
            break
    return short_label[:max_len - 2] + '..'


def format_diff_text(diff_result):
    """Format N-snapshot comparison as a box-drawn terminal table.

    :param diff_result: Result dict from compare_snapshots()
    :type diff_result: dict

    :returns: The rendered multi-line table
    :rtype: str
    """
    labels = diff_result['labels']
    files = diff_result['files']
    summary = diff_result['summary']

    max_col = 50

    short_labels = [_shorten_label(lb, max_col - 2) for lb in labels]

    field_w = len('Field') + 2
    for entry in files:
        for field in entry['fields']:
            field_w = max(field_w, len(f'  {field}') + 2)

    col_ws = [len(sl) + 2 for sl in short_labels]
    for entry in files:
        for vals in entry['fields'].values():
            for i, val in enumerate(vals):
                cell = str(val) if val is not None else ABSENT
                col_ws[i] = max(col_ws[i], len(cell) + 2)
    col_ws = [min(width, max_col) for width in col_ws]

    widths = [field_w] + col_ws

    top = _hline(widths, '┌', '┬', '┐')
    mid = _hline(widths, '├', '┼', '┤')
    dbl = _hline(widths, '╞', '╪', '╡', fill='═')
    bottom = _hline(widths, '└', '┴', '┘')

    lines = []
    lines.append('')
    lines.append(top)
    lines.append(_data_row(['Field'] + short_labels, widths))

    if not files:
        lines.append(mid)
        lines.append(_span_row('(no differences)', widths))
    else:
        for entry in files:
            lines.append(dbl)
            lines.append(_span_row(f'>> {entry["path"]}', widths))
            lines.append(mid)
            for field, vals in entry['fields'].items():
                cells = [f'  {field}']
                for j, val in enumerate(vals):
                    cell = str(val) if val is not None else ABSENT
                    if len(cell) > col_ws[j] - 2:
                        cell = cell[:col_ws[j] - 4] + '..'
                    cells.append(cell)
                lines.append(_data_row(cells, widths))

    lines.append(bottom)
    lines.append(
        f' {summary["changed_files"]} changed, '
        f'{summary["unchanged_files"]} unchanged, '
        f'{summary["total_files"]} total'
    )
    lines.append('')

    return '\n'.join(lines)

# vim: set et ts=4 sw=4 :
