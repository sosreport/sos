# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Ata(Plugin, IndependentPlugin):

    short_desc = 'ATA and IDE information'

    plugin_name = "ata"
    profiles = ('storage', 'hardware')

    packages = ('hdparm', 'smartmontools')

    def setup(self):
        self.add_copy_spec('/proc/ide')
        cmd_list = [
            "hdparm %(dev)s",
            "smartctl -a %(dev)s",
            "smartctl -a %(dev)s -j",
            "smartctl -l scterc %(dev)s",
            "smartctl -l scterc %(dev)s -j"
        ]
        self.add_device_cmd(cmd_list, devices='block',
                            whitelist=['sd.*', 'hd.*'])


# vim: set et ts=4 sw=4 :
