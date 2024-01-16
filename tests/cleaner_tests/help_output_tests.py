# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageOneOutputTest


class CleanHelpTest(StageOneOutputTest):
    """Basic check to make sure --help works with clean

    :avocado: tags=stageone
    """

    sos_cmd = 'clean --help'

    def test_all_help_sections_present(self):
        self.assertOutputContains('Global Options:')
        self.assertOutputContains('Cleaner/Masking Options:')
        self.assertOutputContains('TARGET                The directory or '
                                  'archive to obfuscate')


class MaskHelpTest(CleanHelpTest):
    """The same test, but ensuring the use of the 'mask' alias works. In
    reality this is more testing argparse rather than anything else, but it
    is still good to ensure the aliases remain working

    :avocado: tags=stageone
    """

    sos_cmd = 'mask --help'
