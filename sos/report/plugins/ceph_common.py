# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
from socket import gethostname


class Ceph_Common(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH common'

    plugin_name = 'ceph_common'
    profiles = ('storage', 'virt', 'container')

    containers = ('ceph-(mon|rgw|osd).*',)
    ceph_hostname = gethostname()

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common',
        'calamari-server',
        'librados2'
    )

    services = (
        'ceph-nfs@pacemaker',
        'ceph-mds@%s' % ceph_hostname,
        'ceph-mon@%s' % ceph_hostname,
        'ceph-mgr@%s' % ceph_hostname,
        'ceph-radosgw@*',
        'ceph-osd@*'
    )

    # This check will enable the plugin regardless of being
    # containerized or not
    files = ('/etc/ceph/ceph.conf',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        self.add_file_tags({
            '.*/ceph.conf': 'ceph_conf',
            '/var/log/ceph/ceph.log.*': 'ceph_log',
        })

        if not all_logs:
            self.add_copy_spec("/var/log/calamari/*.log",)
        else:
            self.add_copy_spec("/var/log/calamari",)

        self.add_copy_spec([
            "/var/log/ceph/ceph.log",
            "/var/log/ceph/ceph.audit.log*",
            "/var/log/calamari/*.log",
            "/etc/ceph/",
            "/etc/calamari/",
            "/var/lib/ceph/tmp/",
        ])

        self.add_cmd_output([
            "ceph -v",
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
