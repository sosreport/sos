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
                self.add_cmd_output("%s %s %d" % (cmd, subcmd, channel))

        # raw 0x30 0x65: Get HDD drive Fault LED State
        # raw 0x30 0xb0: Get LED Status

        self.add_cmd_output([
            "%s raw 0x30 0x65" % cmd,
            "%s raw 0x30 0xb0" % cmd,
            "%s sel info" % cmd,
            "%s sel elist" % cmd,
            "%s sel list -v" % cmd,
            "%s sensor list" % cmd,
            "%s chassis status" % cmd,
            "%s lan print" % cmd,
            "%s fru print" % cmd,
            "%s mc info" % cmd,
            "%s sdr info" % cmd
        ])

# vim: set et ts=4 sw=4 :
