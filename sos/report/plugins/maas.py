# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin, PluginOpt


class Maas(Plugin, UbuntuPlugin):

    short_desc = 'Ubuntu Metal-As-A-Service'

    plugin_name = 'maas'
    profiles = ('sysmgmt',)
    packages = ('maas', 'maas-common')

    services = (
        # For the deb:
        'maas-dhcpd',
        'maas-dhcpd6',
        'maas-http',
        'maas-proxy',
        'maas-rackd',
        'maas-regiond',
        'maas-syslog',
        # MAAS 3.5 deb:
        'maas-temporal',
        'maas-apiserver',
        'maas-agent',
        # For the pre-3.5 snap:
        'snap.maas.supervisor',
        # MAAS 3.5 snap uses `snap.maas.pebble` service, but it's not
        # included here to prevent automatic journald log collection.
    )

    option_list = [
        PluginOpt('profile-name', default='', val_type=str,
                  desc='Name of the remote API'),
        PluginOpt('url', default='', val_type=str,
                  desc='URL of the remote API'),
        PluginOpt('credentials', default='', val_type=str,
                  desc='Credentials, or the API key')
    ]

    def _has_login_options(self):
        return self.get_option("url") and self.get_option("credentials") \
            and self.get_option("profile-name")

    def _remote_api_login(self):
        ret = self.exec_cmd(
            "maas login %s %s %s" % (
                self.get_option("profile-name"),
                self.get_option("url"),
                self.get_option("credentials")
            )
        )

        return ret['status'] == 0

    def _is_snap_installed(self):
        maas_pkg = self.policy.package_manager.pkg_by_name('maas')
        if maas_pkg:
            return maas_pkg['pkg_manager'] == 'snap'
        return False

    def setup(self):
        self._is_snap = self._is_snap_installed()
        if self._is_snap:
            self.add_cmd_output([
                'snap info maas',
                'maas status'
            ])

            if self.is_service("snap.maas.pebble"):
                # Because `snap.maas.pebble` is not in the services
                # tuple to prevent timeouts caused by log collection,
                # service status and logs are collected here.
                self.add_service_status("snap.maas.pebble")
                since = self.get_option("since") or "-1days"
                self.add_journal(units="snap.maas.pebble", since=since)

            # Don't send secrets
            self.add_forbidden_path("/var/snap/maas/current/bind/session.key")
            self.add_copy_spec([
                "/var/snap/maas/common/log",
                "/var/snap/maas/common/snap_mode",
                "/var/snap/maas/current/*.conf",
                "/var/snap/maas/current/bind",
                "/var/snap/maas/current/http",
                "/var/snap/maas/current/supervisord",
                "/var/snap/maas/current/preseeds",
                "/var/snap/maas/current/proxy",
                "/var/snap/maas/current/rsyslog",
            ])
        else:
            self.add_copy_spec([
                "/etc/squid-deb-proxy",
                "/etc/maas",
                "/var/lib/maas/dhcp*",
                "/var/lib/maas/http/*.conf",
                "/var/lib/maas/*.conf",
                "/var/lib/maas/rsyslog",
                "/var/log/maas*",
                "/var/log/upstart/maas-*",
            ])
            self.add_cmd_output([
                "apt-cache policy maas-*",
                "apt-cache policy python-django-*",
            ])

        if self.is_installed("maas-region-controller"):
            self.add_cmd_output([
                "maas-region dumpdata",
            ])

        if self._has_login_options():
            if self._remote_api_login():
                self.add_cmd_output("maas %s commissioning-results list" %
                                    self.get_option("profile-name"))
            else:
                self._log_error(
                    "Cannot login into MAAS remote API with provided creds.")

    def postproc(self):
        if self._is_snap:
            regiond_path = "/var/snap/maas/current/maas/regiond.conf"
        else:
            regiond_path = "/etc/maas/regiond.conf"
        self.do_file_sub(regiond_path,
                         r"(database_pass\s*:\s*)(.*)",
                         r"\1********")

# vim: set et ts=4 sw=4 :
