# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Gdm(Plugin, IndependentPlugin):

    short_desc = 'GNOME display manager'

    plugin_name = 'gdm'
    profiles = ('desktop',)
    packages = ('gdm', 'gdm3',)
    services = ('gdm',)

    def setup(self):
        self.add_copy_spec([
            "/etc/gdm/*",
            "/etc/gdm3/*"
        ])

# vim: set et ts=4 sw=4 :
