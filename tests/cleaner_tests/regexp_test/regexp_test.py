# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest

MOCK_FILE = '/tmp/sos-test-regexp.txt'


class RegexpTest(StageTwoReportTest):
    """Test custom regexp obfuscation feature using --regexp-file option.

    Tests that user-defined regular expression patterns from a config file
    are properly loaded and applied to obfuscate sensitive data.

    :avocado: tags=stagetwo
    """

    install_plugins = ['regexp']
    sos_cmd = '--clean -o regexp --no-update'
    # Place mock file with test data and regexp config file
    files = [
        ('sos-test-regexp.txt', MOCK_FILE),
        ('regexp_patterns.conf', '/etc/sos/cleaner/regexp_patterns.conf')
    ]

    def test_shorthost_pattern_with_comma(self):
        """Test pattern: shorthost host=([^,\\s]+)(?:,|$)"""
        self.assertFileCollected(MOCK_FILE)
        # Verify the pattern matched and obfuscated
        self.assertFileHasContent(MOCK_FILE, 'host=obfuscatedshorthost')
        # Verify original value is not present
        self.assertFileNotHasContent(MOCK_FILE, 'host=SECRET,')
        # Verify the rest of the line is preserved
        self.assertFileHasContent(MOCK_FILE, 'os=rhel9')

    def test_shorthost_pattern_at_eol(self):
        """Test pattern matches at end of line"""
        self.assertFileHasContent(MOCK_FILE, 'host=obfuscatedshorthost')
        self.assertFileNotHasContent(MOCK_FILE, 'host=SECRETHOST')

    def test_shorthost_pattern_no_match_with_space(self):
        """Test pattern does NOT match when delimiter is missing"""
        # This line should NOT be obfuscated because no comma or EOL
        # after value
        self.assertFileHasContent(
            MOCK_FILE, 'host=okhost due to the space'
        )

    def test_hostspace_pattern_uppercase(self):
        """Test pattern: hostspace HOST (\\S+)"""
        self.assertFileHasContent(MOCK_FILE, 'HOST obfuscatedhostspace')
        self.assertFileNotHasContent(MOCK_FILE, 'HOST VALUE')

    def test_hostspace_pattern_alphanumeric(self):
        """Test pattern matches alphanumeric values"""
        self.assertFileHasContent(MOCK_FILE, 'HOST obfuscatedhostspace')
        self.assertFileNotHasContent(MOCK_FILE, 'HOST val4ue')

    def test_obfuscation_consistency(self):
        """Test same value gets same obfuscation across file"""
        content = self.get_file_content(MOCK_FILE)
        lines = content.splitlines()

        # Find lines with obfuscatedshorthost
        obfuscated_values = []
        for line in lines:
            if 'host=obfuscatedshorthost' in line:
                # Extract the obfuscated value
                import re
                match = re.search(r'host=(obfuscatedshorthost\d+)', line)
                if match:
                    obfuscated_values.append(match.group(1))

        # lines 4, 8, 11, 23 and 26 do match, so 5 matches should be found
        self.assertEqual(
            len(obfuscated_values), 5,
            f"Expected 5 obfuscated values, "
            f"found {len(obfuscated_values)}"
        )

        # 2nd and 4th should be identical (both are "SECRET")
        self.assertEqual(
            obfuscated_values[1], obfuscated_values[3],
            "Same input value 'SECRET' should get same obfuscation"
        )

        # Third should be different (it's "ANOTHER")
        self.assertNotEqual(
            obfuscated_values[0], obfuscated_values[2],
            "Different input values should get different obfuscations"
        )

    def test_different_keywords_independent_counters(self):
        """Test different keywords have independent counters"""
        content = self.get_file_content(MOCK_FILE)

        # Both shorthost and hostspace should start from 0
        self.assertRegex(content, r'obfuscatedshorthost0')
        self.assertRegex(content, r'obfuscatedhostspace0')
