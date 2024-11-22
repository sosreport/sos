# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Pam(Plugin):

    short_desc = 'Pluggable Authentication Modules'

    plugin_name = "pam"
    profiles = ('security', 'identity', 'system')
    verify_packages = ('pam_.*',)
    security_libs = ""

    def setup(self):

        self.add_file_tags({
            '/etc/pam.d/password-auth': 'password_auth',
            '/etc/security/limits.*.conf': 'limits_conf'
        })

        self.add_copy_spec([
            "/etc/pam.d",
            "/etc/security",
            '/etc/authselect/authselect.conf',
        ])
        self.add_cmd_output([
            "pam_tally2",
            "faillock"
        ])

        self.add_dir_listing(self.security_libs)


class RedHatPam(Pam, RedHatPlugin):
    security_libs = "/lib*/security"

    def setup(self):
        super().setup()
        self.add_cmd_output(["authselect current"])


class DebianPam(Pam, DebianPlugin, UbuntuPlugin):
    security_libs = "/lib/x86_64-linux-gnu/security"


# vim: set et ts=4 sw=4 :
