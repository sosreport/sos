# Copyright (C) 2018 Masco Kaliyamoorthy <mkaliyam@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.plugins import Plugin, RedHatPlugin


class Skydive(Plugin, RedHatPlugin):
    """Skydive, a network topology and protocols analyzer
    """

    plugin_name = "skydive"
    profiles = ('network', )
    files = (
        '/usr/bin/skydive',
        '/etc/skydive/skydive.yml',
    )

    password_warn_text = " (password visible in process listings)"

    option_list = [
        ("username", "skydive user name", "", ""),
        ("password", "skydive password" + password_warn_text, "", ""),
        ("analyzer", "skydive analyzer address", "", ""),
    ]

    def setup(self):
        self.limit = self.get_option("log_size")
        self.add_copy_spec("/etc/skydive/skydive.yml")
        self.add_copy_spec("/var/log/skydive.log", sizelimit=self.limit)

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
        self.add_cmd_output(status_cmd,
                            suggest_filename="skydive_status_api")
# vim: set et ts=4 sw=4 :
