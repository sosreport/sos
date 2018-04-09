# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class SunRPC(Plugin):
    """Sun RPC service
    """

    plugin_name = "sunrpc"
    profiles = ('system', 'storage', 'network', 'nfs')
    service = None

    def check_enabled(self):
        if self.policy.default_runlevel() in \
                self.policy.runlevel_by_service(self.service):
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
