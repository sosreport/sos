# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class SunRPC(Plugin, IndependentPlugin):

    short_desc = 'Sun RPC service'

    plugin_name = "sunrpc"
    profiles = ('system', 'storage', 'network', 'nfs')
    packages = ('rpcbind',)

    def setup(self):
        self.add_cmd_output("rpcinfo -p localhost")
        self.add_copy_spec('/sys/kernel/debug/sunrpc')

# vim: set et ts=4 sw=4 :
