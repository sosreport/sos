# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import unittest
from unittest.mock import Mock, patch

from sos.report.plugins.ata import (
    Ata, _parse_scan_json, _scan_commands, _scan_targets)


JSON_SCAN = """{
  "json_format_version": [1, 0],
  "smartctl": {"version": [7, 2]},
  "devices": [
    {"name": "/dev/sda", "info_name": "/dev/sda",
     "type": "scsi", "protocol": "SCSI"},
    {"name": "/dev/sdb", "info_name": "/dev/sdb [SAT]",
     "type": "sat", "protocol": "ATA"},
    {"name": "/dev/bus/1", "info_name": "/dev/bus/1 [megaraid_disk_08] [SAT]",
     "type": "sat+megaraid,8", "protocol": "ATA"},
    {"name": "/dev/bus/1", "info_name": "/dev/bus/1 [megaraid_disk_14] [SAT]",
     "type": "sat+megaraid,14", "protocol": "ATA"}
  ]
}"""

JSON_SCAN_COMMANDS = [
    'smartctl --xall --device=scsi /dev/sda',
    'smartctl --xall --device=sat /dev/sdb',
    'smartctl --all --device=sat+megaraid,8 /dev/bus/1',
    'smartctl --xall --device=sat+megaraid,8 /dev/bus/1',
    'smartctl --all --device=sat+megaraid,14 /dev/bus/1',
    'smartctl --xall --device=sat+megaraid,14 /dev/bus/1',
    'smartctl --xall /dev/sdc',
]


class SmartctlScanTest(unittest.TestCase):

    def test_parse_json(self):
        self.assertEqual(_parse_scan_json(JSON_SCAN), [
            ('/dev/sda', 'scsi'),
            ('/dev/sdb', 'sat'),
            ('/dev/bus/1', 'sat+megaraid,8'),
            ('/dev/bus/1', 'sat+megaraid,14'),
        ])

    def test_parse_json_skips_open_error(self):
        output = JSON_SCAN.replace(
            '"protocol": "SCSI"}',
            '"protocol": "SCSI", "open_error": "Permission denied"}')
        self.assertEqual(len(_parse_scan_json(output)), 3)

    def test_parse_json_invalid_output(self):
        self.assertIsNone(_parse_scan_json('smartctl: invalid option --json'))

    def test_scan_targets(self):
        block_devs = {'/dev/sda', '/dev/sdb', '/dev/sr0'}
        entries = [
            ('/dev/sda', 'scsi'),
            ('/dev/sdb', 'sat'),
            ('/dev/bus/1', 'sat+megaraid,8'),
            ('/dev/bus/1', 'sat+megaraid,14'),
            ('/dev/nvme0', 'nvme'),
            ('/dev/sr0', 'ata'),
            ('/dev/st0', 'scsi'),
            ('/dev/sg0', 'areca,1/E'),
        ]
        self.assertEqual(_scan_targets(entries, block_devs), [
            ('/dev/sda', 'scsi', True),
            ('/dev/sdb', 'sat', True),
            ('/dev/bus/1', 'sat+megaraid,8', False),
            ('/dev/bus/1', 'sat+megaraid,14', False),
            ('/dev/sg0', 'areca,1/E', False),
        ])

    def test_scan_targets_multiple_controllers(self):
        entries = [
            ('/dev/bus/15', 'sat+megaraid,0'),
            ('/dev/bus/0', 'sat+megaraid,0'),
            ('/dev/bus/0', 'sat+megaraid,4'),
            ('/dev/bus/0', 'sat+megaraid,0'),
        ]
        targets = _scan_targets(entries, set())
        self.assertEqual(targets, [
            ('/dev/bus/15', 'sat+megaraid,0', False),
            ('/dev/bus/0', 'sat+megaraid,0', False),
            ('/dev/bus/0', 'sat+megaraid,4', False),
        ])

    def test_scan_commands(self):
        block_devs = {'/dev/sda', '/dev/sdb', '/dev/sdc', '/dev/sr0'}
        entries = [
            ('/dev/sda', 'scsi'),
            ('/dev/sdb', 'sat'),
            ('/dev/bus/1', 'sat+megaraid,8'),
            ('/dev/bus/1', 'sat+megaraid,14'),
            ('/dev/nvme0', 'nvme'),
            ('/dev/sr0', 'ata'),
            ('/dev/st0', 'scsi'),
            ('/dev/sg0', 'areca,1/E'),
        ]
        targets = _scan_targets(entries, block_devs)
        self.assertEqual(_scan_commands(targets, block_devs), [
            'smartctl --xall --device=scsi /dev/sda',
            'smartctl --xall --device=sat /dev/sdb',
            'smartctl --all --device=sat+megaraid,8 /dev/bus/1',
            'smartctl --xall --device=sat+megaraid,8 /dev/bus/1',
            'smartctl --all --device=sat+megaraid,14 /dev/bus/1',
            'smartctl --xall --device=sat+megaraid,14 /dev/bus/1',
            'smartctl --all --device=areca,1/E /dev/sg0',
            'smartctl --xall --device=areca,1/E /dev/sg0',
            'smartctl --xall /dev/sdc',
        ])


class CollectScannedDisksTest(unittest.TestCase):

    def _plugin(self):
        plugin = Ata.__new__(Ata)
        plugin.sysroot = '/'
        plugin.devices = {
            'storage': {
                'block': ['/dev/sda', '/dev/sdb', '/dev/sdc', '/dev/sr0']
            }
        }
        plugin.exec_cmd = Mock()
        plugin.add_string_as_file = Mock()
        plugin.add_cmd_output = Mock()
        plugin._log_info = Mock()
        return plugin

    def _commands(self, plugin):
        return [call[0][0] for call in plugin.add_cmd_output.call_args_list]

    @patch('sos.report.plugins.ata.is_executable', return_value=True)
    def test_collect_json(self, _):
        plugin = self._plugin()
        plugin.exec_cmd.return_value = {'status': 0, 'output': JSON_SCAN}
        plugin._collect_scanned_disks()

        plugin.exec_cmd.assert_called_once_with(
            'smartctl --scan-open --json', timeout=60)
        plugin.add_string_as_file.assert_called_once_with(
            JSON_SCAN, 'smartctl_--scan-open.json', plug_dir=True)
        self.assertEqual(self._commands(plugin), JSON_SCAN_COMMANDS)

    @patch('sos.report.plugins.ata.is_executable', return_value=True)
    def test_collect_invalid_json(self, _):
        plugin = self._plugin()
        plugin.exec_cmd.return_value = {
            'status': 0, 'output': 'invalid json'}
        plugin._collect_scanned_disks()

        plugin.exec_cmd.assert_called_once_with(
            'smartctl --scan-open --json', timeout=60)
        plugin._log_info.assert_called_once()
        plugin.add_string_as_file.assert_not_called()
        plugin.add_cmd_output.assert_not_called()

    @patch('sos.report.plugins.ata.is_executable', return_value=True)
    def test_collect_scan_timeout(self, _):
        plugin = self._plugin()
        plugin.exec_cmd.return_value = {'status': 124, 'output': ''}
        plugin._collect_scanned_disks()

        plugin.add_string_as_file.assert_not_called()
        plugin.add_cmd_output.assert_not_called()

    @patch('sos.report.plugins.ata.is_executable', return_value=False)
    def test_collect_without_smartctl(self, _):
        plugin = self._plugin()
        plugin._collect_scanned_disks()

        plugin.exec_cmd.assert_not_called()
        plugin.add_string_as_file.assert_not_called()
        plugin.add_cmd_output.assert_not_called()


if __name__ == '__main__':
    unittest.main()
