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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Ceph(Plugin, RedHatPlugin, UbuntuPlugin):
    """CEPH distributed storage
    """

    plugin_name = 'ceph'
    profiles = ('storage', 'virt')

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
        all_logs = self.get_option("all_logs")
        limit = self.get_option("log_size")

        if not all_logs:
            self.add_copy_spec([
                "/var/log/ceph/*.log",
                "/var/log/radosgw/*.log",
                "/var/log/calamari/*.log"
            ], sizelimit=limit)
        else:
            self.add_copy_spec([
                "/var/log/ceph/",
                "/var/log/calamari",
                "/var/log/radosgw"
            ], sizelimit=limit)

        self.add_copy_spec([
            "/etc/ceph/",
            "/etc/calamari/",
            "/var/lib/ceph/",
            "/var/run/ceph/"
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
            "ceph report",
            "ceph osd df tree",
            "ceph fs dump --format json-pretty",
            "ceph fs ls",
            "ceph pg dump",
            "ceph health detail --format json-pretty",
            "ceph osd crush show-tunables",
            "ceph-disk list"
        ])

        self.add_forbidden_path("/etc/ceph/*keyring*")
        self.add_forbidden_path("/var/lib/ceph/*keyring*")
        self.add_forbidden_path("/var/lib/ceph/*/*keyring*")
        self.add_forbidden_path("/var/lib/ceph/*/*/*keyring*")
        self.add_forbidden_path("/var/lib/ceph/osd/*")
        self.add_forbidden_path("/var/lib/ceph/mon/*")

# Excludes temporary ceph-osd mount location like
# /var/lib/ceph/tmp/mnt.XXXX from sos collection.
# In the /var/lib/ceph/tmp/ can still other files of potential
# interest exists, so exclude only known temporary mount locations.

        self.add_forbidden_path("/var/lib/ceph/tmp/*mnt*")
        self.add_forbidden_path("/etc/ceph/*bindpass*")

# vim: set et ts=4 sw=4 :
