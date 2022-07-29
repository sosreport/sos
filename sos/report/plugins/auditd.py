# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Auditd(Plugin, IndependentPlugin):

    short_desc = 'Audit daemon information'

    plugin_name = 'auditd'
    profiles = ('system', 'security')

    packages = ('audit',)

    def setup(self):
        self.add_copy_spec([
            "/etc/audit/auditd.conf",
            "/etc/audit/audit.rules",
            "/etc/audit/audit-stop.rules",
            "/etc/audit/rules.d/",
            "/etc/audit/plugins.d/",
            "/etc/audisp/",
        ])
        self.add_cmd_output([
            "ausearch --input-logs -m avc,user_avc,fanotify -ts today",
            "auditctl -s",
            "auditctl -l"
        ])

        config_file = "/etc/audit/auditd.conf"
        log_file = "/var/log/audit/audit.log"
        try:
            with open(config_file, 'r') as cf:
                for line in cf.read().splitlines():
                    if not line:
                        continue
                    words = line.split('=')
                    if words[0].strip() == 'log_file':
                        log_file = words[1].strip()
        except IOError as error:
            self._log_error('Could not open conf file %s: %s' %
                            (config_file, error))

        if not self.get_option("all_logs"):
            self.add_copy_spec(log_file)
        else:
            self.add_copy_spec(log_file+'*')

# vim: set et ts=4 sw=4 :
