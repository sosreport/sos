# Copyright (C) 2016 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Dracut(Plugin, RedHatPlugin):

    short_desc = 'Dracut initramfs generator'

    plugin_name = "dracut"
    packages = ("dracut",)
    profiles = ("boot",)

    def setup(self):
        self.add_copy_spec([
            "/etc/dracut.conf",
            "/etc/dracut.conf.d"
        ])

        self.add_cmd_output([
            "dracut --list-modules",
            "dracut --print-cmdline"
        ])

# vim: set et ts=4 sw=4 :
