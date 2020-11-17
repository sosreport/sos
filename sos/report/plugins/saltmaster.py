# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class SaltMaster(Plugin, IndependentPlugin):

    short_desc = 'Salt Master'

    plugin_name = 'saltmaster'
    profiles = ('sysmgmt',)

    packages = ('salt-master', 'salt-api',)

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/salt")
        else:
            self.add_copy_spec("/var/log/salt/master")

        self.add_copy_spec("/etc/salt")
        self.add_forbidden_path("/etc/salt/pki/*/*.pem")
        self.add_cmd_output("salt-key --list all")

    def postproc(self):
        regexp = r'((?m)^\s+.*(pass|secret|(?<![A-z])key(?![A-z])).*:\ ).+$'
        subst = r'$1******'
        self.do_path_regex_sub("/etc/salt/*", regexp, subst)

# vim: set et ts=4 sw=4 :
