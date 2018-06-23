# Copyright (C) 2016 Red Hat, Inc., Pratik Bandarkar <pbandark@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Grafana(Plugin, RedHatPlugin):
    """Fetch Grafana configuration, logs and CLI output
    """
    plugin_name = "grafana"
    profiles = ('services', 'openstack', 'openstack_controller')

    packages = ('graphana',)

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/grafana/*.log")
        else:
            self.add_copy_spec("/var/log/grafana/*.log")

        self.add_cmd_output([
            "grafana-cli plugins ls",
            "grafana-cli plugins list-remote",
            "grafana-cli -v",
            "grafana-server -v",
        ])

        self.add_copy_spec([
            "/etc/grafana/",
            "/etc/sysconfig/grafana-server",
        ])

    def postproc(self):
        protect_keys = [
            "admin_password", "secret_key"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/grafana/grafana.ini",
                               regexp, r"\1*********")
