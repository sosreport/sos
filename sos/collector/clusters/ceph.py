# Copyright (C) 2022 Red Hat Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json

from sos.collector.clusters import Cluster


class ceph(Cluster):
    """
    This cluster profile is for Ceph Storage clusters, and is primarily
    built around Red Hat Ceph Storage 5. Nodes are enumerated via `cephadm`; if
    your Ceph deployment uses cephadm but is not RHCS 5, this profile may work
    as intended, but it is not currently guaranteed to do so. If you are using
    such an environment and this profile does not work for you, please file a
    bug report detailing what is failing.

    By default, all nodes in the cluster will be returned for collection. This
    may not be desirable, so users are encouraged to use the `labels` option
    to specify a colon-delimited set of ceph node labels to restrict the list
    of nodes to.

    For example, using `-c ceph.labels=osd:mgr` will return only nodes labeled
    with *either* `osd` or `mgr`.
    """

    cluster_name = 'Ceph Storage Cluster'
    sos_plugins = [
        'ceph_common',
    ]
    sos_options = {'log-size': 50}
    packages = ('cephadm',)
    option_list = [
        ('labels', '', 'Colon delimited list of labels to select nodes with')
    ]

    def get_nodes(self):
        self.nodes = []
        ceph_out = self.exec_primary_cmd(
            'cephadm shell -- ceph orch host ls --format json',
            need_root=True
        )

        if not ceph_out['status'] == 0:
            self.log_error(
                f"Could not enumerate nodes via cephadm: {ceph_out['output']}"
            )
            return self.nodes

        nodes = json.loads(ceph_out['output'].splitlines()[-1])
        _labels = [lab for lab in self.get_option('labels').split(':') if lab]
        for node in nodes:
            if _labels and not any(_l in node['labels'] for _l in _labels):
                self.log_debug(f"{node} filtered from list due to labels")
                continue
            self.nodes.append(node['hostname'])

        return self.nodes

# vim: set et ts=4 sw=4 :
