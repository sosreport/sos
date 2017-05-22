# Copyright (C) 2016 Red Hat, Inc., Pratik Bandarkar <pbandark@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin


class Grafana(Plugin, RedHatPlugin):
    """Fetch Grafana configuration, logs and CLI output
    """
    plugin_name = "grafana"
    profiles = ('services', 'openstack', 'openstack_controller')

    packages = ('graphana',)

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/grafana/*.log",
                               sizelimit=self.get_option("log_size"))
        else:
            self.add_copy_spec("/var/log/grafana/*.log",
                               sizelimit=self.get_option("log_size"))

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
