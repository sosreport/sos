## Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackGlance(Plugin):
    """OpenStackGlance related information
    """
    plugin_name = "openstack-glance"

    option_list = [("log", "gathers openstack glance logs", "slow", True),
                   ("db", "gathers openstack glance db", "slow", True),
                   ("nopw", "dont gathers glance passwords", "slow", True)]

    def setup(self):
        if self.option_enabled("db"):
            self.add_cmd_output(
                "glance-manage db_version",
                suggest_filename="glance_db_version")

        self.add_copy_specs(["/etc/glance/"])

        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/glance/"])

    def postproc(self):
        if self.option_enabled("nopw"):
            self.do_file_sub('/etc/glance/glance-api.conf',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/glance/glance-api.conf',
                            r"(?m)^(sql_connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                            r"\1\2:******@\6")
            self.do_file_sub('/etc/glance/glance-registry.conf',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/glance/glance-registry.conf',
                            r"(?m)^(sql_connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                            r"\1\2:******@\6")


class DebianOpenStackGlance(OpenStackGlance, DebianPlugin, UbuntuPlugin):
    """OpenStackGlance related information for Debian based distributions
    """

    glance = False
    packages = ('glance',
                'glance-api',
                'glance-client',
                'glance-common',
                'glance-registry',
                'python-glance',
                'python-glanceclient')

    def check_enabled(self):
        self.glance = self.is_installed("glance")
        return self.glance

    def setup(self):
        super(DebianOpenStackGlance, self).setup()


class RedHatOpenStackGlance(OpenStackGlance, RedHatPlugin):
    """OpenStackGlance related information for Red Hat distributions
    """

    glance = False
    packages = ('openstack-glance',
                'python-glance',
                'python-glanceclient')

    def check_enabled(self):
        self.glance = self.is_installed("openstack-glance")
        return self.glance

    def setup(self):
        super(RedHatOpenStackGlance, self).setup()
