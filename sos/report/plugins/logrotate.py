# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class LogRotate(Plugin, IndependentPlugin):

    short_desc = 'LogRotate service'

    plugin_name = 'logrotate'
    profiles = ('system',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/crond"

    def setup(self):
        self.add_cmd_output("logrotate --debug /etc/logrotate.conf",
                            suggest_filename="logrotate_debug")
        self.add_copy_spec([
            "/etc/logrotate*",
            "/var/lib/logrotate.status",
            "/var/lib/logrotate/logrotate.status",
            self.var_puppet_gen + "/etc/logrotate-crond.conf",
            self.var_puppet_gen + "/var/spool/cron/root"
        ])

# vim: set et ts=4 sw=4 :
