# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Frr(Plugin, RedHatPlugin):

    short_desc = 'Frr routing service'

    plugin_name = 'frr'
    profiles = ('network',)

    files = ('/etc/frr/zebra.conf',)
    packages = ('frr',)

    def setup(self):
        self.add_copy_spec("/etc/frr/")

# vim: set et ts=4 sw=4 :
