# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import glob


class CephOSD(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH osd'

    plugin_name = 'ceph_osd'
    profiles = ('storage', 'virt', 'container')
    containers = ('ceph-osd.*',)

    def check_enabled(self):
        return True if glob.glob('/var/lib/ceph/osd/*/*') else False

    def setup(self):
        self.add_file_tags({
            '/var/log/ceph/ceph-osd.*.log': 'ceph_osd_log',
        })

        # Only collect OSD specific files
        self.add_copy_spec([
            "/var/log/ceph/ceph-osd*.log",
            "/var/log/ceph/ceph-volume*.log",

            "/var/lib/ceph/osd/",
            "/var/lib/ceph/bootstrap-osd/",

            "/run/ceph/ceph-osd*"
        ])

        self.add_cmd_output([
            "ceph-disk list",
            "ceph-volume lvm list",
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
