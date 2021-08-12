# Copyright (C) 2018 Masco Kaliyamoorthy <mkaliyam@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt
import os


class Skydive(Plugin, RedHatPlugin):

    short_desc = 'Skydive network topology and protocol analyzer'

    plugin_name = "skydive"
    profiles = ('network', )
    files = (
        '/usr/bin/skydive',
        '/etc/skydive/skydive.yml'
    )

    password_warn_text = " (password visible in process listings)"

    option_list = [
        PluginOpt('username', default='', val_type=str,
                  desc='skydive username'),
        PluginOpt('password', default='', val_type=str,
                  desc='skydive password' + password_warn_text),
        PluginOpt('analyzer', default='', val_type=str,
                  desc='skydive analyzer address')
    ]

    def setup(self):
        self.add_copy_spec("/etc/skydive/skydive.yml")
        self.add_copy_spec("/var/log/skydive.log")

        username = (self.get_option("username") or
                    os.getenv("SKYDIVE_USERNAME", "") or
                    os.getenv("OS_USERNAME", ""))
        password = (self.get_option("password") or
                    os.getenv("SKYDIVE_PASSWORD", "") or
                    os.getenv("OS_PASSWORD", ""))
        analyzer = (self.get_option("analyzer") or
                    os.getenv("SKYDIVE_ANALYZER", "localhost:8082"))

        if not all([username, password, analyzer]):
            self.soslog.warning("Some or all of the skydive params are not "
                                "set properly. Skydive status command may "
                                " not work as expected.")

        # Setting all the params in environment variable for
        # skydive client access.
        os.environ["SKYDIVE_USERNAME"] = username
        os.environ["SKYDIVE_PASSWORD"] = password
        os.environ["SKYDIVE_ANALYZER"] = analyzer
        status_cmd = "skydive client status"
        self.add_cmd_output(status_cmd)

# vim: set et ts=4 sw=4 :
