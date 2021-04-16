# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate


class DeviceMapper(Plugin, IndependentPlugin):

    short_desc = 'device-mapper framework'

    plugin_name = 'devicemapper'
    profiles = ('storage',)
    packages = ('device-mapper',)
    kernel_mods = ('dm_mod', )
    files = ('/dev/mapper',)

    def setup(self):
        self.add_cmd_output([
            "dmsetup info -c",
            "dmsetup table",
            "dmsetup status",
            "dmsetup ls --tree",
            "dmsetup udevcookies",
            "dmstats list",
            "dmstats print --allregions"
        ], pred=SoSPredicate(self, kmods=['dm_mod']))

# vim: set et ts=4 sw=4 :
