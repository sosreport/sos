# Copyright (C) 2016 Red Hat, Inc., Pep Turro Mauri <pep@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin
import os.path

# This plugin collects static configuration and runtime information
# about OpenShift Origin based environments, like OpenShift Enterprise 3

# Some clarification on naming:
# OpenShift Origin is the upstream project for OpenShift Enterprise,
# OpenShift Container Platflorm, and Atomic Platform.
#
# However, the name "OpenShift Origin" refers to two different code bases:
#  * Origin M5 and later (https://github.com/openshift/origin)
#    which is upstream for OpenShift 3.x and later.
#    This is what this plugin handles
#  * Origin M4 and earlier (https://github.com/openshift/origin-server)
#    which is upstream for OpenShift 1.x and 2.x.
#    This is handled by the plugin in openshift.py

# Note that this plugin should be used in conjunction with other plugins
# in order to capture relevant data: the Kubernetes plugin for the
# masters, the Docker plugin for the nodes, and also generic
# plugins (e.g. for /etc/sysconfig entries, network setup etc)


class OpenShiftOrigin(Plugin):
    ''' OpenShift Origin '''

    plugin_name = "origin"
    files = None  # file lists assigned after path setup below
    profiles = ('openshift',)

    option_list = [
        ("diag", "run 'oc adm diagnostics' to collect its output",
         'fast', True),
        ("diag-prevent", "set --prevent-modification on 'oc adm diagnostics'",
         'fast', False),
    ]

    master_base_dir = "/etc/origin/master"
    node_base_dir = "/etc/origin/node"
    master_cfg = os.path.join(master_base_dir, "master-config.yaml")
    node_cfg_file = "node-config.yaml"
    node_cfg = os.path.join(node_base_dir, node_cfg_file)
    admin_cfg = os.path.join(master_base_dir, "admin.kubeconfig")
    oc_cmd = "oc"
    oc_cmd_admin = "%s --config=%s" % (oc_cmd, admin_cfg)

    files = (master_cfg, node_cfg)

    # Master vs. node
    #
    # OpenShift Origin/3.x cluster members can be a master, a node, or both at
    # the same time: in most deployments masters are also nodes in order to get
    # access to the pod network, which some functionality (e.g. the API proxy)
    # requires. Therefore the following methods may all evaluate True on a
    # single instance (at least one must evaluate True if this is an OpenShift
    # installation)
    def is_master(self):
        '''Determine if we are on a master'''
        return os.path.exists(self.master_cfg)

    def is_node(self):
        '''Determine if we are on a node'''
        return os.path.exists(self.node_cfg)

    def get_node_kubecfg(self):
        '''Get the full path to the node's kubeconfig file
        from the node's configuration'''

        # If we fail to find a specific kubeconfig we will
        # just point to the general node configuration
        kubeconfig = self.node_cfg_file

        # This should ideally use PyYAML to parse the node's
        # configuration file, but PyYAML is currently not a
        # dependency of sos and we can't guarantee it will
        # be available, so this is a quick&dirty "grep" for
        # the parameter we're looking for
        cfgfile = open(self.node_cfg, 'r')
        for line in cfgfile:
            parts = line.split()
            if len(parts) > 1 and parts[0] == 'masterKubeConfig:':
                kubeconfig = parts[1]
                break
        cfgfile.close()
        return os.path.join(self.node_base_dir, kubeconfig)

    def setup(self):
        # Note that a system can run both a master and a node.
        # See "Master vs. node" above.
        if self.is_master():
            self.add_copy_spec([
                self.master_cfg,
                os.path.join(self.master_base_dir, "*.crt"),
            ])

            # TODO: some thoughts about information that might also be useful
            # to collect. However, these are maybe not needed in general
            # and/or present some challenges (scale, sensitive, ...) and need
            # some more thought. For now just leaving this comment here until
            # we decide if it's worth collecting:
            #
            # General project status:
            #   oc status --all-namespaces   (introduced in OSE 3.2)
            #      -> deemed as not worthy in BZ#1394527
            # Metrics deployment configurations
            #   oc get -o json dc -n openshift-infra
            # Logging stack deployment configurations
            #   oc get -o json dc -n logging
            #
            # Note: Information about nodes, events, pods, and services
            # is already collected by the Kubernetes plugin
            self.add_cmd_output([
                "%s describe projects" % self.oc_cmd_admin,
                "%s get -o json hostsubnet" % self.oc_cmd_admin,
                "%s get -o json clusternetwork" % self.oc_cmd_admin,
                "%s get -o json netnamespaces" % self.oc_cmd_admin,
                # Registry and router configs are typically here
                "%s get -o json dc -n default" % self.oc_cmd_admin,
            ])
            if self.get_option('diag'):
                diag_cmd = "%s adm diagnostics -l 0" % self.oc_cmd_admin
                if self.get_option('diag-prevent'):
                    diag_cmd += " --prevent-modification=true"
                self.add_cmd_output(diag_cmd)
            self.add_journal(units=["atomic-openshift-master",
                                    "atomic-openshift-master-api",
                                    "atomic-openshift-master-controllers"])

            # get logs from the infrastruture pods running in the default ns
            pods = self.get_command_output("%s get pod -o name -n default"
                                           % self.oc_cmd_admin)
            for pod in pods['output'].splitlines():
                self.add_cmd_output("%s logs -n default %s"
                                    % (self.oc_cmd_admin, pod))

        # Note that a system can run both a master and a node.
        # See "Master vs. node" above.
        if self.is_node():
            self.add_copy_spec([
                self.node_cfg,
                os.path.join(self.node_base_dir, "*.crt"),
            ])

            node_kubecfg = self.get_node_kubecfg()
            self.add_cmd_output([
                "%s config view --config=%s" % (self.oc_cmd, node_kubecfg),
                "%s adm diagnostics NodeConfigCheck --node-config=%s"
                % (self.oc_cmd, self.node_cfg)
            ])
            self.add_journal(units="atomic-openshift-node")

    def postproc(self):
        # Clear env values from objects that can contain sensitive data
        # Sample JSON content:
        #           {
        #              "name": "MYSQL_PASSWORD",
        #              "value": "mypassword"
        #           },
        # This will mask values when the "name" looks susceptible of
        # values worth obfuscating, i.e. if the name contains strings
        # like "pass", "pwd", "key" or "token".
        env_regexp = r'(?P<var>{\s*"name":\s*[^,]*' \
                     r'(pass|pwd|key|token|cred|secret' \
                     r'|PASS|PWD|KEY|TOKEN|CRED|SECRET)[^,]*,' \
                     r'\s*"value":)[^}]*'
        self.do_cmd_output_sub('oc*json', env_regexp, r'\g<var> "********"')
        # LDAP identity provider
        self.do_file_sub(self.master_cfg,
                         r"(bindPassword:\s*)(.*)",
                         r'\1"********"')
        # github/google/OpenID identity providers
        self.do_file_sub(self.master_cfg,
                         r"(clientSecret:\s*)(.*)",
                         r'\1"********"')


class AtomicOpenShift(OpenShiftOrigin, RedHatPlugin):
    ''' OpenShift Enterprise / OpenShift Container Platform
    '''

    packages = ('atomic-openshift',)

# vim: set et ts=4 sw=4 :
