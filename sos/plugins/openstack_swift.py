## Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
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

import sos.plugintools

class OpenStackSwift(sos.plugintools.PluginBase):
    """OpenstackSwift related information."""

    packages = ('openstack-swift',
                'openstack-swift-account',
                'openstack-swift-container',
                'openstack-swift-object',
                'openstack-swift-proxy',
                'swift',
                'python-swiftclient')

    def setup(self):
        # Swift
        self.addCopySpec("/etc/swift/")


