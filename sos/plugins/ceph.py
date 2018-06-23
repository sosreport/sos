# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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

        if not all_logs:
            self.add_copy_spec([
                "/var/log/ceph/*.log",
                "/var/log/radosgw/*.log",
                "/var/log/calamari/*.log"
            ])
        else:
            self.add_copy_spec([
                "/var/log/ceph/",
                "/var/log/calamari",
                "/var/log/radosgw"
            ])

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

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/var/lib/ceph/*keyring*",
            "/var/lib/ceph/*/*keyring*",
            "/var/lib/ceph/*/*/*keyring*",
            "/var/lib/ceph/osd/*",
            "/var/lib/ceph/mon/*",
            # Excludes temporary ceph-osd mount location like
            # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
            "var/lib/ceph/tmp/*mnt*",
            "/etc/ceph/*bindpass*"
        ])

# vim: set et ts=4 sw=4 :
