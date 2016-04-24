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
    """CEPH distributed storage
    """

    plugin_name = 'ceph'
    profiles = ('storage', 'virt')

    option_list = [
        ("log", "gathers all ceph logs", "slow", False)
    ]

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common',
        'calamari-server',
        'librados2'
    )

    def setup(self):
        self.add_copy_spec([
            "/etc/ceph/",
            "/var/log/ceph/",
            "/var/lib/ceph/",
            "/var/run/ceph/",
            "/etc/calamari/",
            "/var/log/calamari",
            "/var/log/radosgw"
        ])

        self.add_cmd_output([
            "ceph status",
            "ceph health detail",
            "ceph osd tree",
            "ceph osd stat",
            "ceph osd dump",
            "ceph mon stat",
            "ceph mon dump",
            "ceph df",
            "ceph report"
        ])

        self.add_forbidden_path("/etc/ceph/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*/*/*keyring")
        self.add_forbidden_path("/var/lib/ceph/osd/*")
        self.add_forbidden_path("/var/lib/ceph/osd/mon/*")

# vim: set et ts=4 sw=4 :
