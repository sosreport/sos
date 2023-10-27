# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import re

from sos.report.plugins import Plugin, IndependentPlugin


class Salt(Plugin, IndependentPlugin):

    short_desc = 'Salt'

    plugin_name = 'salt'
    profiles = ('sysmgmt',)

    packages = ('salt', 'salt-minion', 'venv-salt-minion', 'salt-common',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        if not all_logs:
            self.add_copy_spec("/var/log/salt/minion")
        else:
            self.add_copy_spec("/var/log/salt")

        self.add_copy_spec([
            "/var/log/venv-salt-minion.log",
            "/var/log/salt-ssh.log",
        ])

        self.add_copy_spec([
            "/etc/salt",
            "/etc/venv-salt-minion/",
            "/usr/local/etc/salt",
        ])
        self.add_forbidden_path([
            "/etc/salt/pki/*/*.pem",
            "/etc/venv-salt-minion/pki/*/*.pem",
            "/usr/local/etc/salt/pki/*/*.pem",
        ])

        self.add_cmd_output([
            "systemctl --full status salt-minion",
            "systemctl --full status venv-salt-minion",
            "salt-minion --versions-report",
            "venv-salt-minion --versions-report",
            "salt-call --local grains.items --out yaml",
            "venv-salt-call --local grains.items --out yaml",
        ], timeout=30)

    def postproc(self):
        regexp = r'(^\s+.*(pass|secret|(?<![A-z])key(?![A-z])).*:\ ).+$'
        subst = r'\1******'
        self.do_path_regex_sub("/etc/salt/*", regexp, subst)

        # Obfuscate grain entries like `password: mypass` or
        # `secret: mysecret`
        grain_regexp = re.compile("(^.*(pass|secret|key).*:)(.*)$",
                                  re.MULTILINE)
        self.do_cmd_output_sub("salt-call", grain_regexp, subst)
        self.do_cmd_output_sub("venv-salt-call", grain_regexp, subst)

# vim: set et ts=4 sw=4 :
