# This file is part of the sos project: https://github.com/sosreport/sos
# Copyright (C) 2019 Nick Niehoff <nick.niehoff@canonical.com>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
from sos.plugins import Plugin, UbuntuPlugin


class JujuMachine(Plugin, UbuntuPlugin):
    """ Juju orchestration tool - Machine
    """

    plugin_name = "juju_machine"
    profiles = ("virt", "sysmgmt")

    # Using files instead of packages here because there is no identifying
    # package on a juju machine
    commands = ('/usr/bin/juju-run')
    files = ('/var/log/juju')

    def setup(self):
        # Get juju services, they are uniquely named based on the deployment
        # so we need to parse what their names are:
        cmd = "systemctl --no-pager --all --no-legend list-units juju\\*"
        juju_systemctl_output = self.call_ext_prog(cmd)["output"]
        for line in iter(juju_systemctl_output.splitlines()):
            match = re.match(r"^(juju\S+)\s.*", line)
            if match:
                self.add_journal(units=str(match.group(1)))

        self.add_copy_spec('/var/lib/juju/agents/*/agent.conf')

        # Get a directory listing of /var/log/juju and /var/lib/juju
        self.add_cmd_output([
            'ls -alRh /var/log/juju*',
            'ls -alRh /var/lib/juju*'
        ])

        if self.get_option("all_logs"):
            # /var/lib/juju used to be in the default capture moving here
            # because it usually was way to big.  However, in most cases you
            # want all logs you want this too.
            self.add_copy_spec([
                '/var/log/juju',
                '/var/lib/juju'
            ])
        else:
            # We need this because we want to collect to the limit of all
            # logs in the directory
            self.add_copy_spec("/var/log/juju/*.log")

    def postproc(self):
        agents_path = "/var/lib/juju/agents/*"
        protect_keys = [
            "sharedsecret",
            "apipassword",
            "oldpassword",
            "statepassword",
        ]

        protect_certs = [
            "systemidentity",
            "caprivatekey",
            "controllerkey",
            "controllercert",
            "cacert",
        ]

        # Replace simple yamle sytle "key: value"
        keys_regex = r"((?m)^\s*(%s)\s*:\s*)(.*)" % "|".join(protect_keys)
        # Will match and replace a yaml multiline string that is a certificate
        certs_regex = (
            r"((?m)^\s*(%s)\s*:\s*)(\|\s*\n\s+-+BEGIN (.*)"
            r"-+\s(\s+\S+\n)+\s+-+END )\4(-+)" % "|".join(protect_certs)
        )
        sub_regex = r"\1*********"

        self.do_path_regex_sub(agents_path, keys_regex, sub_regex)
        self.do_path_regex_sub(agents_path, certs_regex, sub_regex)

# vim: set et ts=4 sw=4 :
