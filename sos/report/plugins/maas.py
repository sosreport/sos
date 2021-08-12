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
        # For the snap:
        'snap.maas.supervisor',
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
        return self.exec_cmd('snap list maas')["status"] == 0

    def check_enabled(self):
        if super().check_enabled():
            # deb-based MAAS and existing triggers
            return True
        # Do we have the snap installed?
        return self._is_snap_installed()

    def setup(self):
        self._is_snap = self._is_snap_installed()
        if self._is_snap:
            self.add_cmd_output([
                'snap info maas',
                'maas status'
            ])
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
                "/var/log/apache2*",
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
