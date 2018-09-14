# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Cifs(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """SMB file system information
    """
    plugin_name = 'cifs'
    profiles = ('storage', 'network', 'cifs')
    packages = ['cifs-utils']

    def setup(self):
        self.add_copy_spec([
            "/etc/request-key.d/cifs.spnego.conf",
            "/etc/request-key.d/cifs.idmap.conf",
            "/proc/keys",
            "/proc/fs/cifs/LinuxExtensionsEnabled",
            "/proc/fs/cifs/SecurityFlags",
            "/proc/fs/cifs/Stats",
            "/proc/fs/cifs/DebugData",
        ])

# vim: set et ts=4 sw=4 :
