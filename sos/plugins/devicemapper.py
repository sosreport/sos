# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class DeviceMapper(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """device-mapper framework
    """

    plugin_name = 'devicemapper'
    profiles = ('storage',)
    packages = ('device-mapper',)
    files = ('/dev/mapper',)

    def setup(self):
        self.add_cmd_output([
            "dmsetup info -c",
            "dmsetup table",
            "dmsetup status",
            "dmsetup ls --tree"
        ])

# vim: set et ts=4 sw=4 :
