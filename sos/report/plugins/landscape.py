# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin
import os


class Landscape(Plugin, UbuntuPlugin):

    short_desc = 'Ubuntu Landscape client'

    plugin_name = 'landscape'
    profiles = ('sysmgmt',)
    files = ('/etc/landscape/client.conf', '/etc/landscape/service.conf')
    packages = ('landscape-client', 'landscape-server')

    def setup(self):

        vars_all = [p in os.environ for p in [
                        'LANDSCAPE_API_KEY',
                        'LANDSCAPE_API_SECRET',
                        'LANDSCAPE_API_URI',
                    ]]

        if not (all(vars_all)):
            self.soslog.warning("Not all environment variables set. "
                                "Source the environment file for the user "
                                "intended to connect to the Landscape "
                                "environment so that the landscape-api "
                                "commands can be used.")
        else:
            self.add_cmd_output([
                "landscape-api get-distributions",
                "landscape-api get-apt-sources",
                "landscape-api get-repository-profiles",
                "landscape-api get activites --limit 100",
            ])
            self.add_cmd_output([
                "landscape-api --json get-distributions",
                "landscape-api --json get-apt-sources",
                "landscape-api --json get-repository-profiles",
                "landscape-api --json get activites --limit 100",
            ])

        self.add_copy_spec([
            "/etc/default/landscape-client",
            "/etc/default/landscape-server",
            "/etc/landscape/client.conf",
            "/etc/landscape/service.conf",
            "/etc/landscape/service.conf.old",
            "/var/lib/landscape/landscape-oops/*/OOPS-*"
        ])

        if not self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/landscape/*.log",
                "/var/log/landscape-server/*.log",
            ])
        else:
            self.add_copy_spec([
                "/var/log/landscape",
                "/var/log/landscape-server"
            ])

        self.add_cmd_output([
            "gpg --verify /etc/landscape/license.txt",
            "head -n 5 /etc/landscape/license.txt",
            "lsctl status"
        ])

    def postproc(self):
        self.do_file_sub(
            "/etc/landscape/client.conf",
            r"registration_password(.*)",
            r"registration_password[********]"
        )
        keys = [
            "password",
            "store_password",
            "secret-token",
            "oidc-client-secret",
            "oidc-client-id",
        ]
        self.do_path_regex_sub(
            "/etc/landscape/service.conf*",
            r"(%s) = (.*)" % "|".join(keys),
            r"\1 = [********]"
        )

# vim: set et ts=4 sw=4 :
