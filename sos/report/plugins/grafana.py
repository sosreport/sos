# Copyright (C) 2016 Red Hat, Inc., Pratik Bandarkar <pbandark@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Grafana(Plugin, IndependentPlugin):

    short_desc = 'Fetch Grafana configuration, logs and CLI output'
    plugin_name = "grafana"
    profiles = ('services', 'openstack', 'openstack_controller')

    packages = ('grafana',)

    def _is_snap_installed(self):
        grafana_pkg = self.policy.package_manager.pkg_by_name('grafana')
        if grafana_pkg:
            return grafana_pkg['pkg_manager'] == 'snap'
        return False

    def setup(self):
        self._is_snap = self._is_snap_installed()
        if self._is_snap:
            grafana_cli = "grafana.grafana-cli"
            log_path = "/var/snap/grafana/common/data/log/"
            config_path = "/var/snap/grafana/current/conf/grafana.ini"

            self.add_cmd_output("snap info grafana")
        else:
            grafana_cli = "grafana-cli"
            log_path = "/var/log/grafana/"
            config_path = "/etc/grafana/"

        self.add_cmd_output([
            f'{grafana_cli} plugins ls',
            f'{grafana_cli} plugins list-remote',
            f'{grafana_cli} -v',
            'grafana-server -v',
        ])

        log_file_pattern = "*.log*" if self.get_option("all_logs") else "*.log"

        self.add_copy_spec([
            log_path + log_file_pattern,
            config_path,
            "/etc/sysconfig/grafana-server",
        ])

    def postproc(self):
        protect_keys = [
            "admin_password",
            "secret_key",
            "password",
            "client_secret",
        ]
        inifile = (
            "/var/snap/grafana/current/conf/grafana.ini"
            if self._is_snap
            else "/etc/grafana/grafana.ini"
        )

        regexp = r"(^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub(inifile, regexp, r"\1*********")
