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
    """
    This profile is for use with OpenShift Container Platform (v4) clusters
    instead of the kubernetes profile.

    This profile will favor using the `oc` transport type, which means it will
    leverage a locally installed `oc` binary. This is also how node enumeration
    is done. To instead use SSH to connect to the nodes, use the
    '--transport=control_persist' option.

    Thus, a functional `oc` binary for the user executing sos collect is
    required. Functional meaning that the user can run `oc` commands with
    clusterAdmin privileges.

    If this requires the use of a secondary configuration file, specify that
    path with the 'kubeconfig' cluster option. This config file will also be
    used on a single master node to perform API collections if the `with-api`
    option is enabled (default disabled). If no `kubeconfig` option is given,
    but `with-api` is enabled, the cluster profile will attempt to use a
    well-known default kubeconfig file if it is available on the host.

    Alternatively, provide a clusterAdmin access token either via the 'token'
    cluster option or, preferably, the SOSOCPTOKEN environment variable.

    By default, this profile will enumerate only master nodes within the
    cluster, and this may be changed by overriding the 'role' cluster option.
    To collect from all nodes in the cluster regardless of role, use the form
    -c ocp.role=''.

    Filtering nodes by a label applied to that node is also possible via the
    label cluster option, though be aware that this is _combined_ with the role
    option mentioned above.

    To avoid redundant collections of OCP API information (e.g. 'oc get'
    commands), this profile will attempt to enable the API collections on only
    a single master node. If the none of the master nodes have a functional
    'oc' binary available, *and* the --no-local option is used, that means that
    no API data will be collected.
    """

    cluster_name = 'OpenShift Container Platform v4'
    packages = ('openshift-hyperkube', 'openshift-clients')

    api_collect_enabled = False
    token = None
    project = 'sos-collect-tmp'
    oc_cluster_admin = None
    _oc_cmd = ''

    option_list = [
        ('label', '', 'Colon delimited list of labels to select nodes with'),
        ('role', 'master', 'Colon delimited list of roles to filter on'),
        ('kubeconfig', '', 'Path to the kubeconfig file'),
        ('token', '', 'Service account token to use for oc authorization'),
        ('with-api', False, 'Collect OCP API data from a master node')
    ]

    @property
    def oc_cmd(self):
        if not self._oc_cmd:
            self._oc_cmd = 'oc'
            if self.primary.host.in_container():
                _oc_path = self.primary.run_command(
                    'which oc', chroot=self.primary.host.sysroot
                )
                if _oc_path['status'] == 0:
                    self._oc_cmd = os.path.join(
                        self.primary.host.sysroot,
                        _oc_path['output'].strip().lstrip('/')
                    )
                else:
                    self.log_warn(
                        "Unable to to determine PATH for 'oc' command, "
                        "node enumeration may fail."
                    )
                    self.log_debug("Locating 'oc' failed: %s"
                                   % _oc_path['output'])
            if self.get_option('kubeconfig'):
                self._oc_cmd += " --config %s" % self.get_option('kubeconfig')
            self.log_debug("oc base command set to %s" % self._oc_cmd)
        return self._oc_cmd

    def fmt_oc_cmd(self, cmd):
        """Format the oc command to optionall include the kubeconfig file if
        one is specified
        """
        return "%s %s" % (self.oc_cmd, cmd)

    def _attempt_oc_login(self):
        """Attempt to login to the API using the oc command using a provided
        token
        """
        _res = self.exec_primary_cmd(
            self.fmt_oc_cmd("login --insecure-skip-tls-verify=True --token=%s"
                            % self.token)
        )
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
        ret = self.exec_primary_cmd(
            self.fmt_oc_cmd("new-project %s" % self.project)
        )
        if ret['status'] == 0:
            return True

        self.log_debug("Failed to create project: %s" % ret['output'])
        raise Exception("Failed to create temporary project for collection. "
                        "\nAborting...")

    def cleanup(self):
        """Remove the project we created to execute within
        """
        if self.project:
            ret = self.exec_primary_cmd(
                self.fmt_oc_cmd("delete project %s" % self.project)
            )
            if not ret['status'] == 0:
                self.log_error("Error deleting temporary project: %s"
                               % ret['output'])
            ret = self.exec_primary_cmd(
                self.fmt_oc_cmd("wait namespace/%s --for=delete --timeout=30s"
                                % self.project)
            )
            if not ret['status'] == 0:
                self.log_error("Error waiting for temporary project to be "
                               "deleted: %s" % ret['output'])
            # don't leave the config on a non-existing project
            self.exec_primary_cmd(self.fmt_oc_cmd("project default"))
            self.project = None
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
        if self.opts.transport != 'auto':
            return self.opts.transport
        if is_executable('oc', sysroot=self.primary.host.sysroot):
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

    def _toggle_api_opt(self, node, use_api):
        """In earlier versions of sos, the openshift plugin option that is
        used to toggle the API collections was called `no-oc` rather than
        `with-api`. This older plugin option had the inverse logic of the
        current `with-api` option.

        Use this to toggle the correct plugin option given the node's sos
        version. Note that the use of version 4.2 here is tied to the RHEL
        release (the only usecase for this cluster profile) rather than
        the upstream version given the backports for that downstream.

        :param node:    The node being inspected for API collections
        :type node:     ``SoSNode``

        :param use_api: Should this node enable API collections?
        :type use_api:  ``bool``
        """
        if node.check_sos_version('4.2-16'):
            _opt = 'with-api'
            _val = 'on' if use_api else 'off'
        else:
            _opt = 'no-oc'
            _val = 'off' if use_api else 'on'
        node.plugopts.append("openshift.%s=%s" % (_opt, _val))

    def set_primary_options(self, node):

        node.enable_plugins.append('openshift')
        if not self.get_option('with-api'):
            self._toggle_api_opt(node, False)
            return
        if self.api_collect_enabled:
            # a primary has already been enabled for API collection, disable
            # it among others
            self._toggle_api_opt(node, False)
        else:
            # running in a container, so reference the /host mount point
            master_kube = (
                '/host/etc/kubernetes/static-pod-resources/'
                'kube-apiserver-certs/secrets/node-kubeconfigs/'
                'localhost.kubeconfig'
            )
            _optconfig = self.get_option('kubeconfig')
            if _optconfig and not _optconfig.startswith('/host'):
                _optconfig = '/host/' + _optconfig
            _kubeconfig = _optconfig or master_kube
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
                self._toggle_api_opt(node, True)
                self.api_collect_enabled = True
            elif self.token:
                node.sos_env_vars['SOSOCPTOKEN'] = self.token
                self._toggle_api_opt(node, True)
                self.api_collect_enabled = True
            elif node.file_exists(_kubeconfig):
                # if the file exists, then the openshift sos plugin will use it
                # if the with-api option is turned on
                if not _kubeconfig == master_kube:
                    node.plugopts.append(
                        "openshift.kubeconfig=%s" % _kubeconfig
                    )
                self._toggle_api_opt(node, True)
                self.api_collect_enabled = True
            if self.api_collect_enabled:
                msg = ("API collections will be performed on %s\nNote: API "
                       "collections may extend runtime by 10s of minutes\n"
                       % node.address)
                self.soslog.info(msg)
                self.ui_log.info(msg)

    def set_node_options(self, node):
        # don't attempt OC API collections on non-primary nodes
        self._toggle_api_opt(node, False)

# vim: set et ts=4 sw=4 :
