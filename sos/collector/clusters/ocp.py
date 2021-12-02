# Copyright Red Hat 2021, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from pipes import quote
from sos.collector.clusters import Cluster
from sos.utilities import is_executable


class ocp(Cluster):
    """OpenShift Container Platform v4"""

    cluster_name = 'OpenShift Container Platform v4'
    packages = ('openshift-hyperkube', 'openshift-clients')

    api_collect_enabled = False
    token = None
    project = 'sos-collect-tmp'
    oc_cluster_admin = None

    option_list = [
        ('label', '', 'Colon delimited list of labels to select nodes with'),
        ('role', 'master', 'Colon delimited list of roles to filter on'),
        ('kubeconfig', '', 'Path to the kubeconfig file'),
        ('token', '', 'Service account token to use for oc authorization')
    ]

    def fmt_oc_cmd(self, cmd):
        """Format the oc command to optionall include the kubeconfig file if
        one is specified
        """
        if self.get_option('kubeconfig'):
            return "oc --config %s %s" % (self.get_option('kubeconfig'), cmd)
        return "oc %s" % cmd

    def _attempt_oc_login(self):
        """Attempt to login to the API using the oc command using a provided
        token
        """
        _res = self.exec_primary_cmd("oc login --insecure-skip-tls-verify=True"
                                     " --token=%s" % self.token)
        return _res['status'] == 0

    def check_enabled(self):
        if super(ocp, self).check_enabled():
            return True
        self.token = self.get_option('token') or os.getenv('SOSOCPTOKEN', None)
        if self.token:
            self._attempt_oc_login()
        _who = self.fmt_oc_cmd('whoami')
        return self.exec_primary_cmd(_who)['status'] == 0

    def setup(self):
        """Create the project that we will be executing in for any nodes'
        collection via a container image
        """
        if not self.set_transport_type() == 'oc':
            return

        out = self.exec_primary_cmd(self.fmt_oc_cmd("auth can-i '*' '*'"))
        self.oc_cluster_admin = out['status'] == 0
        if not self.oc_cluster_admin:
            self.log_debug("Check for cluster-admin privileges returned false,"
                           " cannot create project in OCP cluster")
            raise Exception("Insufficient permissions to create temporary "
                            "collection project.\nAborting...")

        self.log_info("Creating new temporary project '%s'" % self.project)
        ret = self.exec_primary_cmd("oc new-project %s" % self.project)
        if ret['status'] == 0:
            return True

        self.log_debug("Failed to create project: %s" % ret['output'])
        raise Exception("Failed to create temporary project for collection. "
                        "\nAborting...")

    def cleanup(self):
        """Remove the project we created to execute within
        """
        if self.project:
            ret = self.exec_primary_cmd("oc delete project %s" % self.project)
            if not ret['status'] == 0:
                self.log_error("Error deleting temporary project: %s"
                               % ret['output'])
            # don't leave the config on a non-existing project
            self.exec_primary_cmd("oc project default")
        return True

    def _build_dict(self, nodelist):
        """From the output of get_nodes(), construct an easier-to-reference
        dict of nodes that will be used in determining labels, primary status,
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

    def set_transport_type(self):
        if is_executable('oc') or self.opts.transport == 'oc':
            return 'oc'
        self.log_info("Local installation of 'oc' not found or is not "
                      "correctly configured. Will use ControlPersist.")
        self.ui_log.warn(
            "Preferred transport 'oc' not available, will fallback to SSH."
        )
        if not self.opts.batch:
            input("Press ENTER to continue connecting with SSH, or Ctrl+C to"
                  "abort.")
        return 'control_persist'

    def get_nodes(self):
        nodes = []
        self.node_dict = {}
        cmd = 'get nodes -o wide'
        if self.get_option('label'):
            labels = ','.join(self.get_option('label').split(':'))
            cmd += " -l %s" % quote(labels)
        res = self.exec_primary_cmd(self.fmt_oc_cmd(cmd))
        if res['status'] == 0:
            if self.get_option('role') == 'master':
                self.log_warn("NOTE: By default, only master nodes are listed."
                              "\nTo collect from all/more nodes, override the "
                              "role option with '-c ocp.role=role1:role2'")
            roles = [r for r in self.get_option('role').split(':')]
            self.node_dict = self._build_dict(res['output'].splitlines())
            for node_name, node in self.node_dict.items():
                if roles:
                    for role in roles:
                        if role == node['roles']:
                            nodes.append(node_name)
                else:
                    nodes.append(node_name)
        else:
            msg = "'oc' command failed"
            if 'Missing or incomplete' in res['output']:
                msg = ("'oc' failed due to missing kubeconfig on primary node."
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

    def check_node_is_primary(self, sosnode):
        if sosnode.address not in self.node_dict:
            return False
        return 'master' in self.node_dict[sosnode.address]['roles']

    def set_primary_options(self, node):
        node.enable_plugins.append('openshift')
        if self.api_collect_enabled:
            # a primary has already been enabled for API collection, disable
            # it among others
            node.plugopts.append('openshift.no-oc=on')
        else:
            _oc_cmd = 'oc'
            if node.host.containerized:
                _oc_cmd = '/host/bin/oc'
                # when run from a container, the oc command does not inherit
                # the default config, so if it's present then pass it here to
                # detect a funcitonal oc command. This is sidestepped in sos
                # report by being able to chroot the `oc` execution which we
                # cannot do remotely
                if node.file_exists('/root/.kube/config', need_root=True):
                    _oc_cmd += ' --kubeconfig /host/root/.kube/config'
            can_oc = node.run_command("%s whoami" % _oc_cmd,
                                      use_container=node.host.containerized,
                                      # container is available only to root
                                      # and if rhel, need to run sos as root
                                      # anyways which will run oc as root
                                      need_root=True)
            if can_oc['status'] == 0:
                # the primary node can already access the API
                self.api_collect_enabled = True
            elif self.token:
                node.sos_env_vars['SOSOCPTOKEN'] = self.token
                self.api_collect_enabled = True
            elif self.get_option('kubeconfig'):
                kc = self.get_option('kubeconfig')
                if node.file_exists(kc):
                    if node.host.containerized:
                        kc = "/host/%s" % kc
                    node.sos_env_vars['KUBECONFIG'] = kc
                    self.api_collect_enabled = True
            if self.api_collect_enabled:
                msg = ("API collections will be performed on %s\nNote: API "
                       "collections may extend runtime by 10s of minutes\n"
                       % node.address)
                self.soslog.info(msg)
                self.ui_log.info(msg)

    def set_node_options(self, node):
        # don't attempt OC API collections on non-primary nodes
        node.plugopts.append('openshift.no-oc=on')

# vim: set et ts=4 sw=4 :
