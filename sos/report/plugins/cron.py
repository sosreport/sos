# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Cron(Plugin, IndependentPlugin):

    short_desc = 'Cron job scheduler'

    plugin_name = "cron"
    profiles = ('system',)
    packages = ('cron', 'anacron', 'chronie')

    files = ('/etc/crontab',)

    def setup(self):
        self.add_copy_spec([
            "/etc/cron*",
            "/var/log/cron",
            "/var/spool/cron"
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/cron*")

        self.add_cmd_output("crontab -l -u root",
                            suggest_filename="root_crontab")

# vim: set et ts=4 sw=4 :
