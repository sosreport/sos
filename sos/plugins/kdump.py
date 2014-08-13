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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class KDump(Plugin):
    """Kdump related information
    """

    plugin_name = "kdump"

    def setup(self):
        self.add_copy_specs([
            "/proc/cmdline"
        ])


class RedHatKDump(KDump, RedHatPlugin):
    """Kdump related information for Red Hat distributions
    """

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    def setup(self):
        self.add_copy_specs([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/var/crash/*/vmcore-dmesg.txt"
        ])


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):
    """Kdump related information for Debian distributions
    """

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        self.add_copy_specs([
            "/etc/default/kdump-tools"
        ])

# vim: et ts=4 sw=4
