# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Nis(Plugin, IndependentPlugin):

    short_desc = 'Network Information Service'
    plugin_name = 'nis'
    profiles = ('identity', 'services')

    files = ('/var/yp', '/etc/ypserv.conf')

    packages = ('ypserv',)

    def setup(self):
        self.add_copy_spec([
            "/etc/yp*.conf",
            "/var/yp/*"
        ])
        self.add_cmd_output("domainname")

# vim: set et ts=4 sw=4 :
