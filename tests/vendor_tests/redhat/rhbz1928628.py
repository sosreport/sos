# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from tests.report_tests.plugin_tests.networking.networking import \
    NetworkingPluginTest


class rhbz1928628(NetworkingPluginTest):
    """
    Only collect an eeprom dump when requested, as otherwise this can cause
    NIC flaps.

    https://bugzilla.redhat.com/show_bug.cgi?id=1928628

    :avocado: tags=stageone
    """

    sos_cmd = '-o networking'

    def test_eeprom_dump_not_collected(self):
        self.assertFileGlobNotInArchive('sos_commands/networking/ethtool_-e*')


class rhbz1928628Enabled(NetworkingPluginTest):
    """
    Enable the option to perform eeprom collection.

    WARNING: it has been noted (via this rhbz) that certain NICs may pause
    during this collection

    :avocado: tags=stageone
    """

    sos_cmd = '-o networking -k networking.eepromdump=on'

    def test_eeprom_dump_collected(self):
        self.assertFileGlobInArchive('sos_commands/networking/ethtool_-e*')
