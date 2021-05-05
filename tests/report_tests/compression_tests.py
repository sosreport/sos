# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageOneReportTest


class AutoCompressionTest(StageOneReportTest):
    """Tests to ensure that 'auto' defaults to lzma, as it is in the standard
    library

    :avocado: tags=stageone
    """

    sos_cmd = '-o kernel -z auto'

    def test_lzma_compressed(self):
        self.assertTrue(self.archive.endswith('.tar.xz'))


class GzipCompressionTest(StageOneReportTest):
    """Tests to ensure that users can manually specify the use of gzip

    :avocado: tags=stageone
    """

    sos_cmd = '-o kernel -z gzip'

    def test_gzip_compressed(self):
        self.assertTrue(self.archive.endswith('.tar.gz'))
