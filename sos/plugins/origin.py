# Copyright (C) 2016 Red Hat, Inc., Pep Turro Mauri <pep@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
         'fast', True),
        ("all-namespaces", "collect dc output for all namespaces", "fast",
         False)
    ]

    master_base_dir = "/etc/origin/master"
    node_base_dir = "/etc/origin/node"
    master_cfg = os.path.join(master_base_dir, "master-config.yaml")
    master_env = os.path.join(master_base_dir, "master.env")
    node_cfg_file = "node-config.yaml"
    node_cfg = os.path.join(node_base_dir, node_cfg_file)
    node_kubeconfig = os.path.join(node_base_dir, "node.kubeconfig")
    static_pod_dir = os.path.join(node_base_dir, "pods")

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

    def is_static_etcd(self):
        '''Determine if we are on a node running etcd'''
        return os.path.exists(os.path.join(self.static_pod_dir, "etcd.yaml"))

    def is_static_pod_compatible(self):
        '''Determine if a node is running static pods'''
        return os.path.exists(self.static_pod_dir)

    def setup(self):
        bstrap_node_cfg = os.path.join(self.node_base_dir,
                                       "bootstrap-" + self.node_cfg_file)
        bstrap_kubeconfig = os.path.join(self.node_base_dir,
                                         "bootstrap.kubeconfig")
        node_certs = os.path.join(self.node_base_dir, "certs", "*")
        node_client_ca = os.path.join(self.node_base_dir, "client-ca.crt")
        admin_cfg = os.path.join(self.master_base_dir, "admin.kubeconfig")
        oc_cmd_admin = "%s --config=%s" % ("oc", admin_cfg)
        static_pod_logs_cmd = "master-logs"

        # Note that a system can run both a master and a node.
        # See "Master vs. node" above.
        if self.is_master():
            self.add_copy_spec([
                self.master_cfg,
                self.master_env,
                os.path.join(self.master_base_dir, "*.crt"),
            ])

            if self.is_static_pod_compatible():
                self.add_copy_spec(os.path.join(self.static_pod_dir, "*.yaml"))
                self.add_cmd_output([
                    "%s api api" % static_pod_logs_cmd,
                    "%s controllers controllers" % static_pod_logs_cmd,
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

            subcmds = [
                "describe projects",
                "adm top images",
                "adm top imagestreams"
            ]

            self.add_cmd_output([
                '%s %s' % (oc_cmd_admin, subcmd) for subcmd in subcmds
            ])

            jcmds = [
                "hostsubnet",
                "clusternetwork",
                "netnamespaces"
            ]

            self.add_cmd_output([
                '%s get -o json %s' % (oc_cmd_admin, jcmd) for jcmd in jcmds
            ])

            if self.get_option('all-namespaces'):
                ocn = self.get_command_output('%s get namespaces'
                                              % oc_cmd_admin)
                ns_output = ocn['output'].splitlines()[1:]
                nmsps = [n.split()[0] for n in ns_output if n]
            else:
                nmsps = [
                    'default',
                    'openshift-web-console',
                    'openshift-ansible-service-broker'
                ]

            self.add_cmd_output([
                '%s get -o json dc -n %s' % (oc_cmd_admin, n) for n in nmsps
            ])

            if self.get_option('diag'):
                diag_cmd = "%s adm diagnostics -l 0" % oc_cmd_admin
                if self.get_option('diag-prevent'):
                    diag_cmd += " --prevent-modification=true"
                self.add_cmd_output(diag_cmd)
            self.add_journal(units=["atomic-openshift-master",
                                    "atomic-openshift-master-api",
                                    "atomic-openshift-master-controllers"])

            # get logs from the infrastruture pods running in the default ns
            pods = self.get_command_output("%s get pod -o name -n default"
                                           % oc_cmd_admin)
            for pod in pods['output'].splitlines():
                self.add_cmd_output("%s logs -n default %s"
                                    % (oc_cmd_admin, pod))

        # Note that a system can run both a master and a node.
        # See "Master vs. node" above.
        if self.is_node():
            self.add_copy_spec([
                self.node_cfg,
                self.node_kubeconfig,
                node_certs,
                node_client_ca,
                bstrap_node_cfg,
                bstrap_kubeconfig,
                os.path.join(self.node_base_dir, "*.crt"),
                os.path.join(self.node_base_dir, "resolv.conf"),
                os.path.join(self.node_base_dir, "node-dnsmasq.conf"),
            ])

            self.add_journal(units="atomic-openshift-node")

        if self.is_static_etcd():
            self.add_cmd_output("%s etcd etcd" % static_pod_logs_cmd)

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
