# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Stunnel(Plugin, IndependentPlugin):

    short_desc = 'Universal SSL Tunnel'
    plugin_name = "stunnel"
    profiles = ('network', 'security')

    packages = ('stunnel',)

    def setup(self):

        self.add_service_status('stunnel*')
        self.add_journal('stunnel*')

        self.add_dir_listing(
            '/var/run/stunnel',
            tags=['ls_var_run_stunnel'],
            recursive=True)

        self.add_copy_spec([
            "/etc/stunnel/*.conf",
            "/var/log/stunnel.log"
        ])

# vim: set et ts=4 sw=4 :
