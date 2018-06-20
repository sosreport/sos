# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os
from stat import ST_SIZE


class NfsServer(Plugin, RedHatPlugin):
    """NFS server information
    """

    plugin_name = 'nfsserver'
    profiles = ('storage', 'network', 'services', 'nfs')

    def check_enabled(self):
        default_runlevel = self.policy.default_runlevel()
        nfs_runlevels = self.policy.runlevel_by_service("nfs")
        if default_runlevel in nfs_runlevels:
            return True

        try:
            exports = os.stat("/etc/exports")[ST_SIZE]
            xtab = os.stat("/var/lib/nfs/xtab")[ST_SIZE]
            if exports or xtab:
                return True
        except OSError:
            pass

        return False

    def setup(self):
        self.add_copy_spec([
            "/etc/exports",
            "/etc/exports.d",
            "/var/lib/nfs/etab",
            "/var/lib/nfs/xtab",
            "/var/lib/nfs/rmtab"
        ])

        self.add_cmd_output([
            "rpcinfo -p localhost",
            "nfsstat -o all",
            "exportfs -v"
        ])


# vim: set et ts=4 sw=4 :
