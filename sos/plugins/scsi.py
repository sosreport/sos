# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Scsi(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """SCSI devices
    """

    plugin_name = 'scsi'
    profiles = ('storage', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/proc/scsi",
            "/etc/stinit.def",
            "/sys/bus/scsi",
            "/sys/class/scsi_host",
            "/sys/class/scsi_disk",
            "/sys/class/scsi_device",
            "/sys/class/scsi_generic"
        ])

        self.add_cmd_output([
            "lsscsi",
            "sg_map -x"
        ])

# vim: set et ts=4 sw=4 :
