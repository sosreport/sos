## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

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


from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class openstack(Plugin):
    """openstack related information
    """
    plugin_name = "openstack"

    optionList = [("log", "gathers all openstack logs", "slow", False)]

class DebianOpenStack(openstack, DebianPlugin, UbuntuPlugin):
    """OpenStack related information for Red Hat distributions
    """

    files = ('/etc/nova/nova.conf','/etc/glance/glance-api.conf','/etc/glance-registry.conf')
    packages = ('nova-common','nova-compute'-server', 'mysql')

    def setup(self):
        self.addCopySpecs([
            "/etc/nova/*",
            "/etc/glance/*",
            "/etc/keystone/*])
        self.addCopySpecs([
            "/var/log/nova/*",
            "/var/log/glance/*",
            "/var/log/keystone/*])

class RedHatOpenStack(openstack, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    files = ('/etc/nova/nova.conf','/etc/glance/glance-api.conf','/etc/glance-registry.conf')
    packages = ('nova-common','nova-compute'-server', 'mysql')

    def setup(self):
        self.addCopySpecs([
            "/etc/nova/*",
            "/etc/glance/*",
            "/etc/keystone/*])
        self.addCopySpecs([
            "/var/log/nova/*",
            "/var/log/glance/*",
            "/var/log/keystone/*])
