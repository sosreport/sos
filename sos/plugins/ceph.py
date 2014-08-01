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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Ceph(Plugin, RedHatPlugin, UbuntuPlugin):
    """information on CEPH
    """

    plugin_name = 'ceph'
    option_list = [
        ("log", "gathers all ceph logs", "slow", False)
    ]

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common'
    )

    def setup(self):
        self.add_copy_specs([
            "/etc/ceph/",
            "/var/log/ceph/"
        ])

        self.add_cmd_outputs([
            "ceph status",
            "ceph health",
            "ceph osd tree",
            "ceph osd stat",
            "ceph osd dump",
            "ceph mon stat",
            "ceph mon dump"
        ])

        self.add_forbidden_path("/etc/ceph/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*keyring")

# vim: et ts=4 sw=4
