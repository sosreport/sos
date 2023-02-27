# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import random
import os


from sos_tests import StageOneReportTest, StageTwoReportTest
from string import ascii_uppercase, digits
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


class JournalSizeLimitTest(StageTwoReportTest):
    """Test that journal size limiting is working and is independent of
    --log-size

    Note: this test will insert over 100MB of garbage into the test system's
    journal

    :avocado: tags=stagetwo
    """

    sos_cmd = '-o logs --journal-size=20 --log-size=10'
    sos_timeout = 500
    packages = {
        'rhel': ['python3-systemd'],
        'ubuntu': ['python3-systemd']
    }

    def pre_sos_setup(self):
        # if the journal is already over our size limit, don't write anything
        # new to it
        from systemd import journal
        _reader = journal.Reader()
        _size = _reader.get_usage() / 1024 / 1024
        if _size > 20:
            return
        # write 20MB at a time to side-step rate/size limiting on some distros
        # write over 20MB to ensure we will actually size limit inside sos,
        # allowing for any compression or de-dupe systemd does
        sosfd = journal.stream('sos-testing')
        rsize = 10 * 1048576
        for i in range(2):
            # generate 10MB, write it, then write it in reverse.
            # Spend less time generating new strings
            rand = ''.join(random.choice(ascii_uppercase + digits) for _ in range(rsize))
            sosfd.write(rand + '\n')
            # sleep to avoid burst rate-limiting
            sleep(5)
            sosfd.write(rand[::-1] + '\n')

    def test_journal_size_limit(self):
        journ = 'sos_commands/logs/journalctl_--no-pager'
        self.assertFileCollected(journ)
        jsize = os.stat(self.get_name_in_archive(journ)).st_size
        assert jsize <= 20971520, "Collected journal is larger than 20MB (size: %s)" % jsize

    def test_journal_tailed_and_linked(self):
        tailed = self.get_name_in_archive('sos_strings/logs/journalctl_--no-pager.tailed')
        self.assertFileExists(tailed)
        journ = self.get_name_in_archive('sos_commands/logs/journalctl_--no-pager')
        assert os.path.islink(journ), "Journal in sos_commands/logs is not a symlink"
