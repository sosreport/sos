# Copyright (C) 2015 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2015 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Etcd(Plugin, RedHatPlugin):
    """The etcd plugin collects information from the etcd key-value store. It
    is primarily used by Kubernetes/OpenShift clusters and is often run inside
    a container within the cluster.

    Collections will default to executing within an `etcdctl` container, if one
    is present, and only execute on the host if such a container is not
    currently running. The `etcdctl` name preference is adopted from OpenShift
    Container Platform deployments.

    This plugin is written for etcd v3 and later.
    """

    short_desc = 'etcd plugin'

    plugin_name = 'etcd'
    packages = ('etcd',)
    profiles = ('container', 'system', 'services', 'cluster')
    files = ('/etc/etcd/etcd.conf',)
    containers = ('etcdctl', 'etcd')
    services = ('etcd',)

    def setup(self):

        etcd_con = None
        for con in self.containers:
            if self.get_container_by_name(con):
                etcd_con = con
                break

        self.add_file_tags({
            '/etc/etcd/etcd.conf': 'etcd_conf'
        })

        self.add_forbidden_path([
            '/etc/etcd/ca',
            '/etc/etcd/*.key'
        ])

        self.add_dir_listing('/var/lib/etcd/', container=etcd_con,
                             recursive=True)
        self.add_copy_spec('/etc/etcd', container=etcd_con)

        subcmds = [
           'version',
           'member list',
           'alarm list',
           'endpoint status',
           'endpoint health'
        ]

        self.add_cmd_output(
            [f"etcdctl {sub}" for sub in subcmds],
            container=etcd_con
        )

# vim: et ts=5 sw=4
