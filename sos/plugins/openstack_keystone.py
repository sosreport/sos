## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

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

import sos.plugintools


class OpenStackKeystone(sos.plugintools.PluginBase):
    """openstack keystone related information
    """

    optionList = [("log", "gathers openstack keystone logs", "slow", True),
                   ("nopw", "dont gathers keystone passwords", "slow", True)]

    packages = ('openstack-keystone',
                'python-keystone',
                'python-django-openstack-auth',
                'python-keystoneclient')

    def setup(self):
        self.addCopySpecs([
            "/etc/keystone/default_catalog.templates",
            "/etc/keystone/keystone.conf",
            "/etc/keystone/logging.conf",
            "/etc/keystone/policy.json"
        ])

        if self.getOption("log"):
            self.addCopySpec("/var/log/keystone/")

    def postproc(self):
        self.doRegexSub('/etc/keystone/keystone.conf',
                    r"(?m)^(admin_password.*=)(.*)",
                    r"\1 ******")
        self.doRegexSub('/etc/keystone/keystone.conf',
                    r"(?m)^(admin_token.*=)(.*)",
                    r"\1 ******")
        self.doRegexSub('/etc/keystone/keystone.conf',
                    r"(?m)^(connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                    r"\1\2:******@\6")
        self.doRegexSub('/etc/keystone/keystone.conf',
                    r"(?m)^(password.*=)(.*)",
                    r"\1 ******")
        self.doRegexSub('/etc/keystone/keystone.conf',
                    r"(?m)^(ca_password.*=)(.*)",
                    r"\1 ******")


