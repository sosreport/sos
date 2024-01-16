# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageOneReportTest


class CollectManualTest(StageOneReportTest):
    """Test to ensure that collect() is working for plugins that
    directly call it as part of their collections

    :avocado: tags=stageone
    """

    sos_cmd = '-o unpackaged,python -k python.hashes'
    # unpackaged is only a RedHatPlugin
    redhat_only = True

    def test_unpackaged_list_collected(self):
        self.assertFileCollected('sos_commands/unpackaged/unpackaged')

    def test_python_hashes_collected(self):
        self.assertFileCollected('sos_commands/python/digests.json')

    def test_no_strings_dir(self):
        self.assertFileNotCollected('sos_strings/')

    def test_manifest_collections_correct(self):
        pkgman = self.get_plugin_manifest('unpackaged')
        self.assertTrue(
            any(c['name'] == 'unpackaged' for c in pkgman['collections'])
        )
        pyman = self.get_plugin_manifest('python')
        self.assertTrue(
            any(c['name'] == 'digests.json' for c in pyman['collections'])
        )
