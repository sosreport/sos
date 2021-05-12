# Copyright Red Hat 2021, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from pipes import quote
from sos.collector.clusters import Cluster


class ocp(Cluster):
    """OpenShift Container Platform v4"""

    cluster_name = 'OpenShift Container Platform v4'
    packages = ('openshift-hyperkube', 'openshift-clients')

    option_list = [
        ('label', '', 'Colon delimited list of labels to select nodes with'),
        ('role', '', 'Colon delimited list of roles to select nodes with'),
        ('kubeconfig', '', 'Path to the kubeconfig file')
    ]

    def fmt_oc_cmd(self, cmd):
        """Format the oc command to optionall include the kubeconfig file if
        one is specified
        """
        if self.get_option('kubeconfig'):
            return "oc --config %s %s" % (self.get_option('kubeconfig'), cmd)
        return "oc %s" % cmd

    def check_enabled(self):
        if super(ocp, self).check_enabled():
            return True
        _who = self.fmt_oc_cmd('whoami')
        return self.exec_master_cmd(_who)['status'] == 0

    def _build_dict(self, nodelist):
        """From the output of get_nodes(), construct an easier-to-reference
        dict of nodes that will be used in determining labels, master status,
        etc...

        :param nodelist:        The split output of `oc get nodes`
        :type nodelist:         ``list``

        :returns:           A dict of nodes with `get nodes` columns as keys
        :rtype:             ``dict``
        """
        nodes = {}
        if 'NAME' in nodelist[0]:
            # get the index of the fields
            statline = nodelist.pop(0).split()
            idx = {}
            for state in ['status', 'roles', 'version', 'os-image']:
                try:
                    idx[state] = statline.index(state.upper())
                except Exception:
                    pass
            for node in nodelist:
                _node = node.split()
                nodes[_node[0]] = {}
                for column in idx:
                    nodes[_node[0]][column] = _node[idx[column]]
        return nodes

    def get_nodes(self):
        nodes = []
        self.node_dict = {}
        cmd = 'get nodes -o wide'
        if self.get_option('label'):
            labels = ','.join(self.get_option('label').split(':'))
            cmd += " -l %s" % quote(labels)
        res = self.exec_master_cmd(self.fmt_oc_cmd(cmd))
        if res['status'] == 0:
            roles = [r for r in self.get_option('role').split(':')]
            self.node_dict = self._build_dict(res['stdout'].splitlines())
            for node in self.node_dict:
                if roles:
                    for role in roles:
                        if role in node:
                            nodes.append(node)
                else:
                    nodes.append(node)
        else:
            msg = "'oc' command failed"
            if 'Missing or incomplete' in res['stdout']:
                msg = ("'oc' failed due to missing kubeconfig on master node."
                       " Specify one via '-c ocp.kubeconfig=<path>'")
            raise Exception(msg)
        return nodes

    def set_node_label(self, node):
        if node.address not in self.node_dict:
            return ''
        for label in ['master', 'worker']:
            if label in self.node_dict[node.address]['roles']:
                return label
        return ''

    def check_node_is_master(self, sosnode):
        if sosnode.address not in self.node_dict:
            return False
        return 'master' in self.node_dict[sosnode.address]['roles']

    def set_master_options(self, node):
        node.opts.enable_plugins.append('openshift')
