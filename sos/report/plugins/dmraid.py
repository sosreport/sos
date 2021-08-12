# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Dmraid(Plugin, IndependentPlugin):

    short_desc = 'dmraid software RAID'

    plugin_name = 'dmraid'
    profiles = ('hardware', 'storage')
    packages = ('dmraid',)

    option_list = [
        PluginOpt('metadata', default=False, desc='collect dmraid metadata')
    ]

    # V - {-V/--version}
    # b - {-b|--block_devices}
    # r - {-r|--raid_devices}
    # s - {-s|--sets}
    # t - [-t|--test]
    # a - {-a|--activate} {y|n|yes|no}
    # D - [-D|--dump_metadata]
    dmraid_options = ['V', 'b', 'r', 's', 'tay']

    def setup(self):
        for opt in self.dmraid_options:
            self.add_cmd_output("dmraid -%s" % (opt,))
        if self.get_option("metadata"):
            metadata_path = self.get_cmd_output_path("metadata")
            self.add_cmd_output("dmraid -rD", runat=metadata_path,
                                chroot=self.tmp_in_sysroot())

# vim: set et ts=4 sw=4 :
