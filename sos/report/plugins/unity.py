# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class unity(Plugin, UbuntuPlugin):

    short_desc = 'Unity'

    plugin_name = 'unity'
    profiles = ('hardware', 'desktop')

    packages = (
        'nux-tools',
        'unity'
    )

    def setup(self):
        self.add_cmd_output("/usr/lib/nux/unity_support_test -p")

# vim: set et ts=4 sw=4 :
