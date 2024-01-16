# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import re

from sos_tests import StageTwoReportTest


class FullCleanTest(StageTwoReportTest):
    """Run an unrestricted report execution through sos clean, ensuring that
    our obfuscation is reliable across arbitrary plugin sets and not just the
    'main' plugins that tend to collect data needing obfuscation

    :avocado: tags=stagetwo
    """

    sos_cmd = '-v --clean'
    sos_timeout = 600
    # replace with an empty placeholder, make sure that this test case is not
    # influenced by previous clean runs
    files = [('default_mapping', '/etc/sos/cleaner/default_mapping')]
    packages = {
        'rhel': ['python3-systemd'],
        'ubuntu': ['python3-systemd']
    }

    def pre_sos_setup(self):
        # ensure that case-insensitive matching of FQDNs and shortnames work
        from systemd import journal
        from socket import gethostname
        host = gethostname()
        short = host.split('.')[0]
        sosfd = journal.stream('sos-testing')
        sosfd.write(
            "This is a test line from sos clean testing. The hostname %s "
            "should not appear, nor should %s in an obfuscated archive. The "
            "shortnames of %s and %s should also not appear."
            % (host.lower(), host.upper(), short.lower(), short.upper())
        )

    def test_private_map_was_generated(self):
        self.assertOutputContains(
            'A mapping of obfuscated elements is available at'
        )
        map_file = re.findall(
            '/.*sosreport-.*-private_map',
            self.cmd_output.stdout
        )[-1]
        self.assertFileExists(map_file)

    def test_tarball_named_obfuscated(self):
        self.assertTrue('obfuscated' in self.archive)

    def test_archive_type_correct(self):
        self.assertSosLogContains('Loaded .* as type sos report directory')

    def test_hostname_not_in_any_file(self):
        host = self.sysinfo['pre']['networking']['hostname']
        short = host.split('.')[0]
        # much faster to just use grep here
        content = self.grep_for_content(host) + self.grep_for_content(short)
        if not content:
            assert True
        else:
            self.fail("Hostname appears in files: %s"
                      % "\n".join(f for f in content))

    def test_no_empty_obfuscations(self):
        # get the private map file name
        map_file = re.findall(
            '/.*sosreport-.*-private_map',
            self.cmd_output.stdout
        )[-1]
        with open(map_file, 'r') as mf:
            map_json = json.load(mf)
        for mapping in map_json:
            for key, val in map_json[mapping].items():
                assert key, "Empty key found in %s" % mapping
                assert val, "%s mapping for '%s' empty" % (mapping, key)

    def test_ip_not_in_any_file(self):
        ip = self.sysinfo['pre']['networking']['ip_addr']
        content = self.grep_for_content(ip)
        if not content:
            assert True
        else:
            new_content = "\n".join(f for f in content)
            self.fail(f'IP appears in files: {new_content}')
