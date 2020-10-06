# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Nfs(Plugin, IndependentPlugin):

    short_desc = 'Network file system information'
    plugin_name = 'nfs'
    profiles = ('storage', 'network', 'nfs')
    packages = ('nfs-utils', )

    def setup(self):
        self.add_copy_spec([
            "/etc/nfsmount.conf",
            "/etc/idmapd.conf",
            "/etc/nfs.conf",
            "/proc/fs/nfsfs/servers",
            "/proc/fs/nfsfs/volumes",
            "/run/sysconfig/nfs-utils",
            "/etc/exports",
            "/etc/exports.d",
            "/var/lib/nfs/etab",
            "/var/lib/nfs/xtab",
            "/var/lib/nfs/rmtab",
        ])

        self.add_cmd_output([
            "rpcinfo -p localhost",
            "nfsstat -o all",
            "exportfs -v",
        ])


# vim: set et ts=4 sw=4 :
