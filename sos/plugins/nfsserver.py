# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

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
import os
from stat import ST_SIZE


class NfsServer(Plugin, RedHatPlugin):
    """NFS server information
    """

    plugin_name = 'nfsserver'
    profiles = ('storage', 'network', 'services', 'nfs')

    def check_enabled(self):
        default_runlevel = self.policy().default_runlevel()
        nfs_runlevels = self.policy().runlevel_by_service("nfs")
        if default_runlevel in nfs_runlevels:
            return True

        try:
            exports = os.stat("/etc/exports")[ST_SIZE]
            xtab = os.stat("/var/lib/nfs/xtab")[ST_SIZE]
            if exports or xtab:
                return True
        except:
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
