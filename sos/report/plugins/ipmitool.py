# Copyright (C) 2016 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin


class IpmiTool(Plugin, RedHatPlugin, DebianPlugin):

    short_desc = 'IpmiTool hardware information'

    plugin_name = 'ipmitool'
    profiles = ('hardware', 'system', )

    packages = ('ipmitool',)

    def setup(self):
        cmd = "ipmitool"
        result = self.collect_cmd_output("ipmitool -I usb mc info")
        if result['status'] == 0:
            cmd += " -I usb"

        for subcmd in ['channel info', 'channel getaccess', 'lan print']:
            for channel in [1, 3]:
                self.add_cmd_output(f"{cmd} {subcmd} {channel}")

        # raw 0x30 0x65: Get HDD drive Fault LED State
        # raw 0x30 0xb0: Get LED Status

        self.add_cmd_output([
            f"{cmd} raw 0x30 0x65",
            f"{cmd} raw 0x30 0xb0",
            f"{cmd} sel info",
            f"{cmd} sel elist",
            f"{cmd} sel list -v",
            f"{cmd} sensor list",
            f"{cmd} chassis status",
            f"{cmd} lan print",
            f"{cmd} fru print",
            f"{cmd} mc info",
            f"{cmd} sdr info",
        ])

# vim: set et ts=4 sw=4 :
