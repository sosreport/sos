## Copyright (C) 2013 Red Hat, Inc.

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

from sos import plugins


class OpenStackHeat(plugins.Plugin):
    """openstack related information
    """
    plugin_name = "openstack-heat"

    option_list = [("log", "gathers openstack-heat logs", "slow", True),
                   ("db", "gathers openstack heat db", "slow", True),
                   ("nopw", "dont gathers heat passwords", "slow", True)]

    def setup(self):
        # Heat
        if self.option_enabled("db"):
            self.add_cmd_output(
                "heat-manage db_version",
                suggest_filename="heat_db_version")

        self.add_copy_specs(["/etc/heat/"])

        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/heat/"])

    def postproc(self):
        if self.option_enabled("nopw"):
            self.do_file_sub('/etc/heat/heat-api-cfn-paste.ini',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/heat/heat-api-cloudwatch-paste.ini',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/heat/heat-api-paste.ini',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/heat/heat-api-cfn.conf',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/heat/heat-api-cloudwatch.conf',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/heat/heat-engine.conf',
                            r"(?m)^(sql_connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                            r"\1\2:******@\6")


class DebianOpenStack(OpenStackHeat,
                      plugins.DebianPlugin,
                      plugins.UbuntuPlugin):
    """OpenStackHeat related information for Debian based distributions."""

    packages = ('heat-api',
                'heat-api-cfn',
                'heat-api-cloudwatch',
                'heat-common',
                'heat-engine',
                'python-heat',
                'python-heatclient')
    heat = False

    def check_enabled(self):
        self.heat = self.is_installed("heat-common")
        return self.heat

class RedHatOpenStack(OpenStackHeat, plugins.RedHatPlugin):
    """OpenStackHeat related information for Red Hat distributions."""

    packages = ('openstack-heat-api',
                'openstack-heat-api-cfn',
                'openstack-heat-api-cloudwatch',
                'openstack-heat-cli',
                'openstack-heat-common',
                'openstack-heat-engine',
                'python-heatclient')
    heat = False

    def check_enabled(self):
        self.heat = self.is_installed("openstack-heat-common")
        return self.heat