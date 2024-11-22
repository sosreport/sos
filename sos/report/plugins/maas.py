# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, UbuntuPlugin


class MAAS(Plugin, UbuntuPlugin):

    short_desc = 'MAAS | Metal as a Service'

    plugin_name = 'maas'
    plugin_timeout = 1800
    profiles = ('sysmgmt',)

    packages = (
        'maas',
        'maas-region-api',
        'maas-region-controller',
        'maas-rack-controller',
        'maas-agent',
    )

    _services = (
        'maas-agent',
        'maas-apiserver',
        'maas-dhcpd',
        'maas-dhcpd6',
        'maas-http',
        'maas-proxy',
        'maas-rackd',
        'maas-regiond',
        'maas-syslog',
        'maas-temporal',
        'maas-temporal-worker',
        'snap.maas.supervisor',
        'snap.maas.pebble',
    )

    def _get_machines_syslog(self, directory):
        if not self.path_exists(directory):
            return []

        # Machine messages are collected with syslog and are stored under:
        #   $template "{{log_dir}}/rsyslog/%HOSTNAME%/%$YEAR%-%$MONTH%-%$DAY%"
        # Collect only the most recent "%$YEAR%-%$MONTH%-%$DAY%"
        # for each "%HOSTNAME%".
        recent = []
        for host_dir in self.listdir(directory):
            host_path = self.path_join(directory, host_dir)
            if not self.path_isdir(host_path):
                continue

            subdirs = [
                self.path_join(host_path, d)
                for d in self.listdir(host_path)
                if self.path_isdir(host_path)
            ]

            if not subdirs:
                continue

            sorted_subdirs = sorted(
                subdirs, key=lambda d: os.stat(d).st_mtime, reverse=True
            )

            all_logs = self.get_option("all_logs")
            since = self.get_option("since")

            if not all_logs and not since:
                recent.append(sorted_subdirs[0])
            else:
                since = since.timestamp() if since else 0
                recent.extend(
                    [d for d in sorted_subdirs if os.stat(d).st_mtime >= since]
                )

        return recent

    def _snap_collect(self):
        self.add_cmd_output([
            'snap info maas',
            'maas status',
        ], snap_cmd=True)

        self.add_forbidden_path([
            "/var/snap/maas/**/*.key",
            "/var/snap/maas/**/*.pem",
            "/var/snap/maas/**/secret",
        ])

        self.add_copy_spec([
            "/var/snap/maas/common/snap_mode",
            "/var/snap/maas/common/log/**/*.log",
            "/var/snap/maas/current/**/*.conf",
            "/var/snap/maas/current/**/*.yaml",
            "/var/snap/maas/current/bind",
            "/var/snap/maas/current/preseeds",
            "/var/snap/maas/current/supervisord/*.log",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/snap/maas/common/log/**/*.log.*",
                "/var/snap/maas/current/supervisord/*.log.*",
            ])

        self.add_copy_spec(
            self._get_machines_syslog(
                "/var/snap/maas/common/log/rsyslog"
            )
        )

    def _deb_collect(self):
        self.add_cmd_output([
            "apt-cache policy maas maas-*",
        ])

        self.add_forbidden_path([
            "/var/lib/maas/**/*.key",
            "/var/lib/maas/**/*.pem",
            "/var/lib/maas/**/secret",
            "/etc/maas/**/*.key",
            "/etc/maas/**/*.pem",
            "/etc/maas/**/secret",
        ])

        self.add_copy_spec([
            "/etc/maas/**/*.conf",
            "/etc/maas/**/*.yaml",
            "/etc/maas/preseeds",
            "/var/lib/maas/**/*.conf",
            "/var/lib/maas/dhcp/*.leases",
            "/var/lib/maas/temporal",
            "/var/log/maas/**/*.log",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/maas/**/*.log.*",
            ])

        self.add_copy_spec(
            self._get_machines_syslog(
                "/var/log/maas/rsyslog"
            )
        )

    def setup(self):
        for service in self._services:
            if self.is_service(service):
                self.add_service_status(service)
                if not self.get_option('all_logs'):
                    since = self.get_option("since") or "-1days"
                    self.add_journal(service, since=since)
                else:
                    self.add_journal(service)

        if self.is_snap:
            self._snap_collect()
        else:
            self._deb_collect()

    def postproc(self):
        self.do_path_regex_sub(
            r"(.*)\.(conf|yaml|yml|toml)$",
            r"((?:.*secret|.*password|.*pass)(?::\s*|=\s*))(.*)",
            r"\1*****"
        )

# vim: set et ts=4 sw=4 :
