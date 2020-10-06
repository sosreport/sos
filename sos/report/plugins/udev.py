# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Udev(Plugin, IndependentPlugin):

    short_desc = 'udev dynamic device management'

    plugin_name = 'udev'
    profiles = ('system', 'hardware', 'boot')

    def setup(self):
        self.add_copy_spec([
            "/etc/udev/udev.conf",
            "/lib/udev/rules.d",
            "/etc/udev/rules.d/*"
        ])

# vim: set et ts=4 sw=4 :
