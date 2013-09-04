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


class OpenStackCinder(Plugin):
    """OpenStackCinder related information
    """
    plugin_name = "openstack-cinder"

    option_list = [("log", "gathers openstack cinder logs", "slow", True),
                   ("db", "gathers openstack cinder db version", "slow", True),
                   ("nopw", "dont gathers cinder passwords", "slow", True)]

    def setup(self):
        if self.option_enabled("db"):
            self.add_cmd_output(
                "cinder-manage db version",
                suggest_filename="cinder_db_version")

        self.add_copy_specs(["/etc/cinder/"])

        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/cinder/"])

    def postproc(self):
        if self.option_enabled("nopw"):
            self.do_file_sub('/etc/cinder/api-paste.ini',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/cinder/cinder.conf',
                            r"(?m)^(admin_password.*=)(.*)",
                            r"\1 ******")
            self.do_file_sub('/etc/cinder/cinder.conf',
                            r"(?m)^(sql_connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                            r"\1\2:******@\6")
            self.do_file_sub('/etc/cinder/cinder.conf',
                            r"(?m)^(rabbit_password.*=)(.*)",
                            r"\1 ******")


class DebianOpenStackCinder(OpenStackCinder, DebianPlugin, UbuntuPlugin):
    """OpenStackCinder related information for Debian based distributions
    """

    cinder = False
    packages = ('cinder-api',
                'cinder-backup',
                'cinder-common',
                'cinder-scheduler',
                'cinder-volume',
                'python-cinder',
                'python-cinderclient')

    def check_enabled(self):
        self.cinder = self.is_installed("cinder-common")
        return self.cinder

    def setup(self):
        super(DebianOpenStackCinder, self).setup()
        self.add_copy_spec("/etc/sudoers.d/cinder_sudoers")

class RedHatOpenStackCinder(OpenStackCinder, RedHatPlugin):
    """OpenStackCinder related information for Red Hat distributions
    """

    cinder = False
    packages = ('openstack-cinder',
                'python-cinder',
                'python-cinderclient')

    def check_enabled(self):
        self.cinder = self.is_installed("openstack-cinder")
        return self.cinder

    def setup(self):
        super(RedHatOpenStackCinder, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/cinder"])
