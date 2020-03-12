# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, UbuntuPlugin


class Maas(Plugin, UbuntuPlugin):
    """Ubuntu Metal-As-A-Service
    """

    plugin_name = 'maas'
    profiles = ('sysmgmt',)
    packages = ('maas', 'maas-common')

    services = (
        'maas-dhcpd',
        'maas-dhcpd6',
        'maas-http',
        'maas-proxy',
        'maas-rackd',
        'maas-regiond',
        'maas-syslog'
    )

    option_list = [
        ('profile-name',
         'The name with which you will later refer to this remote', '', ''),
        ('url', 'The URL of the remote API', '', ''),
        ('credentials',
         'The credentials, also known as the API key', '', '')
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

    def setup(self):
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

        self.add_service_status(self.services)

        for service in self.services:
            self.add_journal(units=service)

        if self.is_installed("maas-region-controller"):
            self.add_cmd_output([
                "maas-region-admin dumpdata",
            ])

        if self._has_login_options():
            if self._remote_api_login():
                self.add_cmd_output("maas %s commissioning-results list" %
                                    self.get_option("profile-name"))
            else:
                self._log_error(
                    "Cannot login into MAAS remote API with provided creds.")

    def postproc(self):
        self.do_file_sub("/etc/maas/regiond.conf",
                         r"(database_pass\s*:\s*)(.*)",
                         r"\1********")

# vim: set et ts=4 sw=4 :
