# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Juju(Plugin, UbuntuPlugin):

    short_desc = 'Juju orchestration tool'

    plugin_name = 'juju'
    profiles = ('virt', 'sysmgmt')

    # Using files instead of packages here because there is no identifying
    # package on a juju machine.
    files = ('/var/log/juju',)

    def setup(self):
        # Juju service names are not consistent through deployments,
        # so we need to use a wildcard to get the correct service names.
        for service in self.get_service_names("juju*"):
            self.add_journal(service)
            self.add_service_status(service)

        # Get agent configs for each agent.
        self.add_copy_spec("/var/lib/juju/agents/*/agent.conf")

        # Get a directory listing of /var/log/juju and /var/lib/juju
        self.add_cmd_output([
            "ls -alRh /var/log/juju*",
            "ls -alRh /var/lib/juju*"
        ])

        if self.get_option("all_logs"):
            # /var/lib/juju used to be in the default capture moving here
            # because it usually was way to big.  However, in most cases you
            # want all logs you want this too.
            self.add_copy_spec([
                "/var/log/juju",
                "/var/lib/juju"
            ])
        else:
            # We need this because we want to collect to the limit of all
            # logs in the directory.
            self.add_copy_spec("/var/log/juju/*.log")

    def postproc(self):
        agents_path = "/var/lib/juju/agents/*"
        protect_keys = [
            "sharedsecret",
            "apipassword",
            "oldpassword",
            "statepassword",
        ]

        # Redact simple yaml style "key: value".
        keys_regex = r"((?m)^\s*(%s)\s*:\s*)(.*)" % "|".join(protect_keys)
        sub_regex = r"\1*********"
        self.do_path_regex_sub(agents_path, keys_regex, sub_regex)
        # Redact certificates
        self.do_file_private_sub(agents_path)

# vim: set et ts=4 sw=4 :
