# Copyright (C) 2016 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class IpmiTool(Plugin, RedHatPlugin, DebianPlugin):
    """IpmiTool hardware information.
    """

    plugin_name = 'ipmitool'
    profiles = ('hardware', 'system', )

    packages = ('ipmitool',)

    def setup(self):
        result = self.get_command_output("ipmitool -I usb mc info")
        have_usbintf = result['status']

        if not have_usbintf:
            cmd = "ipmitool -I usb"
        else:
            cmd = "ipmitool"

        self.add_cmd_output([
            "%s sel info" % cmd,
            "%s sel list" % cmd,
            "%s sensor list" % cmd,
            "%s chassis status" % cmd,
            "%s fru print" % cmd,
            "%s mc info" % cmd,
            "%s sdr info" % cmd
        ])

# vim: set et ts=4 sw=4 :
