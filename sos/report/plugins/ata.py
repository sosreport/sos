# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import re

from sos.report.plugins import Plugin, IndependentPlugin
from sos.utilities import is_executable


# JSON output was introduced in smartmontools 7.0. Older versions do not
# provide scan-based disk collection; block device collection is unaffected.
JSON_SCAN_CMD = 'smartctl --scan-open --json'
_HACKERS_TIMEOUT = 60

DISK_RE = re.compile(r'^/dev/(?:sd|hd)[a-z]+$')
DEFAULT_TYPES = ('ata', 'scsi', 'nvme', 'auto')


def _parse_scan_json(output):
    """Return (device, type) pairs from ``smartctl --scan-open --json``."""
    try:
        devices = json.loads(output)['devices']
        return [
            (device['name'], device['type'])
            for device in devices
            if device.get('name') and device.get('type')
            and not device.get('open_error')
        ]
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _scan_targets(entries, block_devs):
    """Return (device, type, is_block_disk) targets from scan entries."""
    targets = []
    seen = set()
    for dev, dtype in entries:
        is_block_disk = bool(DISK_RE.match(dev))
        if dtype == 'nvme':
            continue
        if dev in block_devs and not is_block_disk:
            continue
        if not is_block_disk and dtype in DEFAULT_TYPES:
            continue
        if (dev, dtype) in seen:
            continue
        seen.add((dev, dtype))
        targets.append((dev, dtype, is_block_disk))
    return targets


def _scan_commands(targets, block_devs):
    """Return smartctl commands for the given scan targets."""
    commands = []
    seen_devs = set()
    for dev, dtype, is_block_disk in targets:
        seen_devs.add(dev)
        if is_block_disk:
            commands.append(f"smartctl --xall --device={dtype} {dev}")
        else:
            commands.append(f"smartctl --all --device={dtype} {dev}")
            commands.append(f"smartctl --xall --device={dtype} {dev}")

    for dev in sorted(block_devs):
        if DISK_RE.match(dev) and dev not in seen_devs:
            commands.append(f"smartctl --xall {dev}")
    return commands


class Ata(Plugin, IndependentPlugin):
    """Collects ATA/IDE information and SMART data.

    SMART data is collected for block devices visible to the operating
    system and for disks reported by ``smartctl --scan-open``, including
    physical disks behind RAID controllers that have no block device node.
    """

    short_desc = 'ATA and IDE information'

    plugin_name = "ata"
    profiles = ('storage', 'hardware')

    packages = ('hdparm', 'smartmontools')
    plugin_timeout = 600

    def setup(self):
        self.add_copy_spec('/proc/ide')
        cmd_list = [
            "hdparm %(dev)s",
            "smartctl -a %(dev)s",
            "smartctl -a %(dev)s -j",
            "smartctl -l scterc %(dev)s",
            "smartctl -l scterc %(dev)s -j"
        ]
        self.add_device_cmd(cmd_list, devices='block',
                            whitelist=['sd.*', 'hd.*'])
        self._collect_scanned_disks()

    def _collect_scanned_disks(self):
        """Collect SMART data for devices found by ``--scan-open``."""
        if not is_executable('smartctl', self.sysroot):
            return

        scan = self.exec_cmd(JSON_SCAN_CMD, timeout=_HACKERS_TIMEOUT)
        if scan['status'] == 124:
            return

        entries = _parse_scan_json(scan['output'])
        if entries is None:
            self._log_info('smartctl --scan-open --json is unsupported or '
                           'returned invalid output; skipping scan-based '
                           'disk collection (smartmontools >= 7.0 is '
                           'required)')
            return

        self.add_string_as_file(scan['output'],
                                'smartctl_--scan-open.json', plug_dir=True)

        block_devs = set(
            self.devices.get('storage', {}).get('block', []))
        targets = _scan_targets(entries, block_devs)
        for cmd in _scan_commands(targets, block_devs):
            self.add_cmd_output(cmd, timeout=_HACKERS_TIMEOUT)


# vim: set et ts=4 sw=4 :
