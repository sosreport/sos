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

        usbtest = self.collect_cmd_output("ipmitool -I usb mc info")
        if usbtest and usbtest['status'] == 0:
            cmd += " -I usb"

        self.add_cmd_output([
            "%s sel info" % cmd,
            "%s sel list" % cmd,
            "%s sensor list" % cmd,
            "%s chassis status" % cmd,
            "%s lan print" % cmd,
            "%s fru print" % cmd,
            "%s mc info" % cmd,
            "%s sdr info" % cmd
        ])

# vim: set et ts=4 sw=4 :
