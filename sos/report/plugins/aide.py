# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Aide(Plugin):

    short_desc = 'Advanced Intrusion Detection Environment'

    plugin_name = "aide"
    profiles = ('system', 'security')

    packages = ('aide',)
    conf_file = "/etc/aide/aide.conf"

    def setup(self):
        self.add_cmd_output(f"aide -c {self.conf_file} --config-check")

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/aide/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/aide/aide.log"
            ])


class RedHatAide(Aide, RedHatPlugin):
    conf_file = "/etc/aide.conf"

    def setup(self):
        super(RedHatAide, self).setup()
        self.add_copy_spec([
            "/etc/aide.conf",
            "/etc/logrotate.d/aide"
        ])


class DebianAide(Aide, DebianPlugin, UbuntuPlugin):
    conf_file = "/etc/aide/aide.conf"

    def setup(self):
        super(DebianAide, self).setup()
        self.add_copy_spec([
            "/etc/aide/",
            "/etc/default/aide"
        ])

# vim: et ts=4 sw=4
