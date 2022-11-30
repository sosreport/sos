# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import random
import os
import sys


from sos_tests import StageOneReportTest, StageTwoReportTest
from time import sleep

class LogsPluginTest(StageOneReportTest):
    """Ensure common collections from the `logs` plugin are properly collected

    :avocado: tags=stageone
    """

    sos_cmd = '-o logs --all-logs'

    def test_journalctl_collections(self):
        self.assertFileCollected('sos_commands/logs/journalctl_--disk-usage')
        self.assertFileCollected('sos_commands/logs/journalctl_--no-pager_--boot')

    def test_journal_runtime_collected(self):
        self.assertFileGlobInArchive('/var/log/journal/*')


class LogsSizeLimitTest(StageTwoReportTest):
    """Test that journal size limiting is working and is independent of
    --log-size

    Note: this test will insert over 100MB of garbage into the test system's
    journal

    :avocado: tags=stagetwo
    """

    sos_cmd = '-o logs'
    sos_timeout = 500
    packages = {
        'rhel': ['python3-systemd'],
        'ubuntu': ['python3-systemd']
    }

    def pre_sos_setup(self):
        # write enough random data to the journal so that the on disk size is
        # over 100MB, thus triggering our size limiting for this test
        from systemd import journal
        j = journal.Reader()
        sosfd = journal.stream('sos-testing')
        # journald default threshold size is 64k
        rsize = 65535
        to_write = ((101 * 1048576) - (j.get_usage()))
        if to_write / 1048576 < 1:
            return
        try:
            # this is unavailable on python < 3.11, but required on 3.11+
            try:
                orig_limit = sys.get_int_max_str_digits()
                sys.set_int_max_str_digits(rsize)
            except Exception:
                # on older runtime, changes not needed
                orig_limit = None
            for i in range(int(to_write / rsize) + 1):
                rand = f"{random.getrandbits(rsize * 4):x}"
                sosfd.write(rand)
        except Exception:
            raise
        finally:
            if orig_limit:
                sys.set_int_max_str_digits(orig_limit)

    def test_journal_size_limit(self):
        journ = 'sos_commands/logs/journalctl_--no-pager'
        self.assertFileCollected(journ)
        jsize = os.stat(self.get_name_in_archive(journ)).st_size
        assert jsize <= 105906176, "Collected journal is larger than 100MB (size: %s)" % jsize
        assert jsize > 27262976, "Collected journal limited by --log-size (size: %s)" % jsize

    def test_journal_tailed_and_linked(self):
        tailed = self.get_name_in_archive('sos_strings/logs/journalctl_--no-pager.tailed')
        self.assertFileExists(tailed)
        journ = self.get_name_in_archive('sos_commands/logs/journalctl_--no-pager')
        assert os.path.islink(journ), "Journal in sos_commands/logs is not a symlink"

    def test_string_not_in_manifest(self):
        # we don't want truncated collections appearing in the strings section
        # of the manifest for the plugin
        manifest = self.get_plugin_manifest('logs')
        self.assertFalse(manifest['strings'])
