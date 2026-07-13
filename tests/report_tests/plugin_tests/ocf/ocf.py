# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class OcfPluginTest(StageTwoReportTest):
    """Ensure that the ocf plugin collects OCF binaries and libraries when
    the standard paths are present on the system.

    :avocado: tags=stagetwo
    """

    files = [
        ('usr_bin_ocf/sample-ocf-bin', '/usr/bin/ocf/sample-ocf-bin'),
        ('usr_lib_ocf/resource.d/heartbeat/Dummy',
         '/usr/lib/ocf/resource.d/heartbeat/Dummy'),
    ]

    sos_cmd = '-o ocf'

    def test_plugin_ran(self):
        self.assertPluginIncluded('ocf')

    def test_usr_bin_ocf_collected(self):
        self.assertFileCollected('/usr/bin/ocf/sample-ocf-bin')

    def test_usr_lib_ocf_collected(self):
        self.assertFileCollected(
            '/usr/lib/ocf/resource.d/heartbeat/Dummy')

    def test_dir_listing_collected(self):
        self.assertFileGlobInArchive('sos_commands/ocf/ls_-alZ_*usr*bin*ocf*')
        self.assertFileGlobInArchive('sos_commands/ocf/ls_-alZ_*usr*lib*ocf*')
