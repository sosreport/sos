# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class NfsGanesha(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """NFS-Ganesha file server information
    """
    plugin_name = 'nfsganesha'
    profiles = ('storage', 'network', 'nfs')
    packages = ('nfs-ganesha')

    def setup(self):
        self.add_copy_spec([
            "/etc/ganesha",
            "/etc/sysconfig/ganesha",
            "/var/run/sysconfig/ganesha",
            "/var/log/ganesha.log",
            "/var/log/ganesha-gfapi.log"
        ])

        self.add_cmd_output([
            "dbus-send --type=method_call --print-reply"
            " --system --dest=org.ganesha.nfsd "
            "/org/ganesha/nfsd/ExportMgr "
            "org.ganesha.nfsd.exportmgr.ShowExports"
        ])

        return


# vim: set et ts=4 sw=4 :
