# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Pam(Plugin):
    """Pluggable Authentication Modules
    """

    plugin_name = "pam"
    profiles = ('security', 'identity', 'system')
    verify_packages = ('pam_.*',)
    security_libs = ""

    def setup(self):
        self.add_copy_spec([
            "/etc/pam.d",
            "/etc/security"
        ])
        self.add_cmd_output([
            "ls -lanF %s" % self.security_libs,
            "pam_tally2",
            "faillock"
        ])


class RedHatPam(Pam, RedHatPlugin):
    security_libs = "/lib*/security"

    def setup(self):
        super(RedHatPam, self).setup()


class DebianPam(Pam, DebianPlugin, UbuntuPlugin):
    security_libs = "/lib/x86_64-linux-gnu/security"

    def setup(self):
        super(DebianPam, self).setup()


# vim: set et ts=4 sw=4 :
