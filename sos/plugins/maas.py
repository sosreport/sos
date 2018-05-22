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

    option_list = [
        ('profile-name',
         'The name with which you will later refer to this remote', '', False),
        ('url', 'The URL of the remote API', '', False),
        ('credentials',
         'The credentials, also known as the API key', '', False)
    ]

    def _has_login_options(self):
        return self.get_option("url") and self.get_option("credentials") \
            and self.get_option("profile-name")

    def _remote_api_login(self):
        ret = self.call_ext_prog("maas login %s %s %s" % (
            self.get_option("profile-name"),
            self.get_option("url"),
            self.get_option("credentials")))

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

# vim: set et ts=4 sw=4 :
