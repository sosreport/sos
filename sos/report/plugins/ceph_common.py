# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from socket import gethostname
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephCommon(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH common'

    plugin_name = 'ceph_common'
    profiles = ('storage', 'virt', 'container', 'ceph')

    containers = ('ceph-(.*-)?(mon|rgw|osd).*',)
    ceph_hostname = gethostname()

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common',
        'calamari-server',
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
    files = ('/etc/ceph/ceph.conf',
             '/var/snap/microceph/*',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        microceph_pkg = self.policy.package_manager.pkg_by_name('microceph')
        if not microceph_pkg:
            self.add_file_tags({
                '.*/ceph.conf': 'ceph_conf',
                '/var/log/ceph(.*)?/ceph.log.*': 'ceph_log',
            })

            if not all_logs:
                self.add_copy_spec([
                    "/var/log/calamari/*.log",
                    "/var/log/ceph/**/ceph.log",
                ])
            else:
                self.add_copy_spec([
                    "/var/log/calamari",
                    "/var/log/ceph/**/ceph.log*",
                ])

            self.add_copy_spec([
                "/var/log/ceph/**/ceph.audit.log*",
                "/etc/ceph/",
                "/etc/calamari/",
                "/var/lib/ceph/tmp/",
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
        else:
            if not all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/ceph.log",
                    "/var/snap/microceph/common/logs/ceph.audit.log",
                ])
            else:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/ceph.log*",
                    "/var/snap/microceph/common/logs/ceph.audit.log*",
                ])

        self.add_cmd_output([
            "ceph -v",
        ])

# vim: set et ts=4 sw=4 :
