# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin


class SunRPC(Plugin):
    """Sun RPC service
    """

    plugin_name = "sunrpc"
    profiles = ('system', 'storage', 'network', 'nfs')
    service = None

    def check_enabled(self):
        if self.policy().default_runlevel() in \
                self.policy().runlevel_by_service(self.service):
            return True
        return False

    def setup(self):
        self.add_cmd_output("rpcinfo -p localhost")
        return


class RedHatSunRPC(SunRPC, RedHatPlugin):

    service = 'rpcbind'

# FIXME: depends on addition of runlevel_by_service (or similar)
# in Debian/Ubuntu policy classes
# class DebianSunRPC(SunRPC, DebianPlugin, UbuntuPlugin):
#    """Sun RPC related information
#    """
#
#    service = 'rpcbind-boot'
#
#    def setup(self):
#        self.add_cmd_output("rpcinfo -p localhost")
#        return

# vim: set et ts=4 sw=4 :
