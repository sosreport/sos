# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin


class Maas(Plugin, UbuntuPlugin):
    """Ubuntu Metal-As-A-Service
    """

    plugin_name = 'maas'
    profiles = ('sysmgmt',)

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
