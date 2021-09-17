# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import glob


class CephMDS(Plugin, RedHatPlugin, UbuntuPlugin):
    short_desc = 'CEPH mds'
    plugin_name = 'ceph_mds'
    profiles = ('storage', 'virt', 'container')
    containers = ('ceph-fs.*',)

    def check_enabled(self):
        return True if glob.glob('/var/lib/ceph/mds/*/*') else False

    def setup(self):
        self.add_file_tags({
            '/var/log/ceph/ceph-mds.*.log': 'ceph_mds_log',
        })

        self.add_copy_spec([
            "/var/log/ceph.log",
            "/var/log/ceph/ceph-mds*.log",
            "/var/lib/ceph/bootstrap-mds/",
            "/var/lib/ceph/mds/",
            "/run/ceph/ceph-mds*",
        ])

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/var/lib/ceph/*keyring*",
            "/var/lib/ceph/*/*keyring*",
            "/var/lib/ceph/*/*/*keyring*",
            "/var/lib/ceph/osd",
            "/var/lib/ceph/mon",
            # Excludes temporary ceph-osd mount location like
            # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
            "/var/lib/ceph/tmp/*mnt*",
            "/etc/ceph/*bindpass*"
        ])

# vim: set et ts=4 sw=4 :
