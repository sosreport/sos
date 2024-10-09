# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class CurtinScrubbedTest(StageTwoReportTest):
    """Ensure that curtin conf is picked up and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """

    sos_cmd = '-o curtin'
    files = [
        ('curtin-install-cfg.yaml', '/root/curtin-install-cfg.yaml'),
        ('curtin-install.log', '/root/curtin-install.log'),
    ]

    key_value_obfuscate = {
        "consumer_key": "yaYmBSUuArGt3JYwHU",
        "token_key": "WCCtp2JewdWkHEDAW6",
        "token_secret": "Bm2k3ZdGxFPUK7aZUpTbkRmKQuACKURR",
    }

    files_collect = [
        '/root/curtin-install-cfg.yaml',
        '/root/curtin-install.log',
    ]

    def test_curtin_confs_collected(self):
        for file in self.files_collect:
            self.assertFileCollected(file)

    def test_curtin_files_scrubbed(self):
        for file in self.files_collect:
            for key, value in self.key_value_obfuscate.items():
                self.assertFileNotHasContent(file, fr"{key}: {value}")
                self.assertFileNotHasContent(file, fr"{key}={value}")
                self.assertFileNotHasContent(file, value)
                self.assertFileHasContent(file, fr"{key}:\*\*\*\*\*\*\*\*\*")
                self.assertFileHasContent(file, fr"{key}=\*\*\*\*\*\*\*\*\*")

# vim: set et ts=4 sw=4 :
