# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Unbound(Plugin, IndependentPlugin):

    short_desc = 'Unbound DNS resolver'

    plugin_name = 'unbound'
    profiles = ('system', 'services', 'network')
    packages = ('unbound', 'unbound-libs')

    def setup(self):
        self.add_copy_spec([
            "/etc/sysconfig/unbound",
            "/etc/unbound/unbound.conf",
            "/usr/lib/tmpfiles.d/unbound.conf",
            "/etc/unbound/conf.d/",
            "/etc/unbound/local.d/",
        ])


# vim: set et ts=4 sw=4 :
