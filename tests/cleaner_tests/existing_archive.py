# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re
import json
from sos_tests import StageTwoReportTest

ARCHIVE = 'sosreport-cleanertest-2021-08-03-qpkxdid'

class ExistingArchiveCleanTest(StageTwoReportTest):
    """Ensure that we can extract an already created archive and clean it the
    same as we would an in-line run of `report --clean`.

    Note that this copies heavily from the full_report_run test.

    :avocado: tags=stagetwo
    """

    sos_cmd = '-v tests/test_data/%s.tar.xz' % ARCHIVE
    sos_component = 'clean'

    def test_obfuscation_log_created(self):
        self.assertFileExists(os.path.join(self.tmpdir, '%s-obfuscation.log' % ARCHIVE))

    def test_archive_type_correct(self):
        with open(os.path.join(self.tmpdir, '%s-obfuscation.log' % ARCHIVE), 'r') as log:
            for line in log:
                if "Loaded %s" % ARCHIVE in line:
                    assert 'as type sos report archive' in line, "Incorrect archive type detected: %s" % line
                    break

    def test_from_cmdline_logged(self):
        with open(os.path.join(self.tmpdir, '%s-obfuscation.log' % ARCHIVE), 'r') as log:
            for line in log:
                if 'From cmdline' in line:
                    assert 'From cmdline: True' in line, "Did not properly log cmdline run"
                    break

    def test_extraction_completed_successfully(self):
        with open(os.path.join(self.tmpdir, '%s-obfuscation.log' % ARCHIVE), 'r') as log:
            for line in log:
                if 'Extracted path is' in line:
                    path = line.split('Extracted path is')[-1].strip()
                    assert path.startswith(self.tmpdir), "Extracted path appears wrong: %s (tmpdir: %s)" % (path, self.tmpdir)
                    return
            self.fail("Extracted path not logged")

    def test_private_map_was_generated(self):
        self.assertOutputContains('A mapping of obfuscated elements is available at')
        map_file = re.findall('/.*sosreport-.*-private_map', self.cmd_output.stdout)[-1]
        self.assertFileExists(map_file)

    def test_tarball_named_obfuscated(self):
        self.assertTrue('obfuscated' in self.archive)

    def test_hostname_not_in_any_file(self):
        # much faster to just use grep here
        content = self.grep_for_content('cleanertest')
        if not content:
            assert True
        else:
            self.fail("Hostname appears in files: %s"
                      % "\n".join(f for f in content))

    def test_no_empty_obfuscations(self):
        # get the private map file name
        map_file = re.findall('/.*sosreport-.*-private_map', self.cmd_output.stdout)[-1]
        with open(map_file, 'r') as mf:
            map_json = json.load(mf)
        for mapping in map_json:
            for key, val in map_json[mapping].items():
                assert key, "Empty key found in %s" % mapping
                assert val, "%s mapping for '%s' empty" % (mapping, key)

    def test_ip_not_in_any_file(self):
        content = self.grep_for_content('10.0.0.15')
        if not content:
            assert True
        else:
            self.fail("IP appears in files: %s" % "\n".join(f for f in content))

    def test_user_is_obfuscated(self):
        """Ensure that the 'testuser1' user created at install is obfuscated
        """
        self.assertFileNotHasContent('var/log/anaconda/journal.log', 'testuser1')

class ExistingArchiveCleanTmpTest(StageTwoReportTest):
    """Continuation of above tests which requires cleaning var / tmp keywords

    Note that this copies heavily from the full_report_run test.

    :avocado: tags=stagetwo
    """

    sos_cmd = '-v --keywords var,tmp,avocado --disable-parsers ip,ipv6,mac,username \
        --no-update tests/test_data/%s.tar.xz' % ARCHIVE
    sos_component = 'clean'

    def test_sys_tmp_not_obfuscated(self):
        """ Ensure that keywords var, tmp and avocado remains in the final archive
        path despite they are parts of the --tmp-dir
        """
        self.assertTrue(self.archive.startswith(os.getenv('AVOCADO_TESTS_COMMON_TMPDIR')))

