# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Salt(Plugin, IndependentPlugin):

    short_desc = 'Salt'

    plugin_name = 'salt'
    profiles = ('sysmgmt',)

    packages = ('salt', 'salt-minion', 'salt-common',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        if not all_logs:
            self.add_copy_spec("/var/log/salt/minion")
        else:
            self.add_copy_spec("/var/log/salt")

        self.add_copy_spec("/etc/salt")
        self.add_forbidden_path("/etc/salt/pki/*/*.pem")

    def postproc(self):
        regexp = r'((?m)^\s+.*(pass|secret|(?<![A-z])key(?![A-z])).*:\ ).+$'
        subst = r'\1******'
        self.do_path_regex_sub("/etc/salt/*", regexp, subst)

# vim: set et ts=4 sw=4 :
