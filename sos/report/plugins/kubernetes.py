# Copyright (C) 2014 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from fnmatch import translate
import re
from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)
import json


class Kubernetes(Plugin):

    short_desc = 'Kubernetes container orchestration platform'

    plugin_name = "kubernetes"
    profiles = ('container',)
    plugin_timeout = 1200

    config_files = [
        "/etc/kubernetes",
        "/run/flannel",
    ]
    resources = [
        'events',
        'deployments',
        'ingresses',
        'pods',
        'pvc',
        'services',
        'daemonsets',
        'replicasets',
        'endpoints',
        'statefulsets',
        'configmaps',
        'serviceaccounts',
        'secrets',
        'jobs',
        'cronjobs',
        'clusterroles',
        'clusterrolebindings'
    ]

    # these are not namespaced, must pull separately.
    global_resources = [
        'sc',
        'pv',
        'roles',
        'rolebindings'
    ]

    option_list = [
        PluginOpt('all', default=False,
                  desc='collect all namespace output separately'),
        PluginOpt('describe', default=False,
                  desc='collect describe output of all resources'),
        PluginOpt('podlogs', default=False,
                  desc='capture stdout/stderr logs from pods'),
        PluginOpt('podlogs-filter', default='', val_type=str,
                  desc='only collect logs from pods matching this pattern')
    ]

    kube_cmd = "kubectl"

    def check_is_master(self):
        """ Check if this is the master node """
        return any(self.path_exists(f) for f in self.files)

    def setup(self):
        self.add_copy_spec(self.config_files)

        self.add_env_var([
            'KUBECONFIG',
            'KUBERNETES_HTTP_PROXY',
            'KUBERNETES_HTTPS_PROXY',
            'KUBERNETES_NO_PROXY'
        ])

        svcs = [
            'kubelet',
            'kube-apiserver',
            'kube-proxy',
            'kube-scheduler',
            'kube-controller-manager',
            'snap.kubelet.daemon',
            'snap.kube-apiserver.daemon',
            'snap.kube-proxy.daemon',
            'snap.kube-scheduler.daemon',
            'snap.kube-controller-manager.daemon'
        ]

        for svc in svcs:
            self.add_journal(units=svc)

        # We can only grab kubectl output from the master
        if not self.check_is_master():
            return

        for subcmd in ['version', 'config view']:
            self.add_cmd_output(
                f'{self.kube_cmd} {subcmd}',
                subdir='cluster-info'
            )

        if self.get_option('all'):
            self.add_cmd_output([
                f"{self.kube_cmd} get -o json {res}"
                for res in self.global_resources
            ], subdir='cluster-info')
        else:
            self.add_cmd_output([
                f"{self.kube_cmd} get {res}"
                for res in self.global_resources
            ], subdir='cluster-info')

        # Get detailed node information
        nodes = self.collect_cmd_output(f"{self.kube_cmd} get nodes",
                                        subdir='cluster-info')
        if nodes['status'] == 0 and self.get_option('describe'):
            for line in nodes['output'].splitlines()[1:]:
                # find first word in the line and ignore empty+blank lines
                words = line.split()
                if not words:
                    continue
                node = words[0]
                self.add_cmd_output(
                    f"{self.kube_cmd} describe node {node}",
                    subdir='cluster-info'
                )

        self.add_cmd_output([
            f"{self.kube_cmd} get -o json nodes",
        ], subdir='cluster-info')

        # Also collect master metrics
        self.add_cmd_output(
            f"{self.kube_cmd} get --raw /metrics",
            subdir='cluster-info'
        )

        # CNV is not part of the base installation, but can be added
        if self.is_installed('kubevirt-virtctl'):
            self.resources.extend(['vms', 'vmis'])
            self.add_cmd_output('virtctl version')

        self.collect_per_resource_details()
        self.collect_all_resources()

    def collect_per_resource_details(self):
        """ Collect details about each resource in all namespaces """
        # get all namespaces in use
        kns = self.collect_cmd_output(f'{self.kube_cmd} get namespaces',
                                      subdir='cluster-info')
        # namespace is the 1st word on line, until the line has spaces only
        kn_output = kns['output'].splitlines()[1:]
        knsps = [n.split()[0] for n in kn_output if n and len(n.split())]

        for nspace in knsps:
            knsp = '--namespace=%s' % nspace
            if self.get_option('all'):
                k_cmd = f'{self.kube_cmd} get -o json {knsp}'

                for res in self.resources:
                    self.add_cmd_output(
                        f'{k_cmd} {res}',
                        subdir=f'cluster-info/{nspace}'
                    )

            if self.get_option('describe'):
                # need to drop json formatting for this
                k_cmd = f'{self.kube_cmd} {knsp}'
                for res in self.resources:
                    if res == 'events':
                        continue
                    ret = self.exec_cmd(f'{k_cmd} get {res}')
                    if ret['status'] == 0:
                        k_list = [k.split()[0] for k in
                                  ret['output'].splitlines()[1:]]
                        for item in k_list:
                            k_cmd = f'{self.kube_cmd} {knsp}'
                            self.add_cmd_output(
                                f'{k_cmd} describe {res} {item}',
                                subdir=f'cluster-info/{nspace}/{res}'
                            )

            if self.get_option('podlogs'):
                k_cmd = f'{self.kube_cmd} get -o json {knsp}'
                ret = self.exec_cmd(f'{k_cmd} pods')
                if ret['status'] == 0:
                    pods = json.loads(ret['output'])
                    # allow shell-style regex
                    reg = (translate(self.get_option('podlogs-filter')) if
                           self.get_option('podlogs-filter') else None)
                    for pod in pods["items"]:
                        if reg and not re.match(reg, pod["metadata"]["name"]):
                            continue
                        _subdir = (f'cluster-info/'
                                   f'{pod["metadata"]["namespace"]}/podlogs/'
                                   f'{pod["metadata"]["name"]}')
                        if "containers" in pod["spec"]:
                            for cont in pod["spec"]["containers"]:
                                pod_name = pod["metadata"]["name"]
                                cont_name = cont["name"]
                                self.add_cmd_output(
                                    f'{self.kube_cmd} {knsp} logs '
                                    f'{pod_name} -c {cont_name}',
                                    subdir=_subdir
                                )
                        if "initContainers" in pod["spec"]:
                            for cont in pod["spec"]["initContainers"]:
                                pod_name = pod["metadata"]["name"]
                                cont_name = cont["name"]
                                self.add_cmd_output(
                                    f'{self.kube_cmd} {knsp} logs '
                                    f'{pod_name} -c {cont_name}',
                                    subdir=_subdir
                                )

    def collect_all_resources(self):
        """ Collect details about all resources """
        if not self.get_option('all'):
            k_cmd = f'{self.kube_cmd} get --all-namespaces=true'
            for res in self.resources:
                self.add_cmd_output(
                    f'{k_cmd} {res}',
                    subdir='cluster-info'
                )

    def postproc(self):
        # First, clear sensitive data from the json output collected.
        # This will mask values when the "name" looks susceptible of
        # values worth obfuscating, i.e. if the name contains strings
        # like "pass", "pwd", "key" or "token"
        env_regexp = r'(?P<var>{\s*"name":\s*[^,]*' \
            r'(pass|pwd|key|token|cred|PASS|PWD|KEY)[^,]*,\s*"value":)[^}]*'
        self.do_cmd_output_sub(self.kube_cmd, env_regexp,
                               r'\g<var> "********"')

        # Next, we need to handle the private keys and certs in some
        # output that is not hit by the previous iteration.
        self.do_cmd_private_sub(self.kube_cmd)


class RedHatKubernetes(Kubernetes, RedHatPlugin):

    # OpenShift Container Platform uses the atomic-openshift-master package
    # to provide kubernetes
    packages = ('kubernetes', 'kubernetes-master', 'atomic-openshift-master')

    files = (
        '/etc/origin/master/admin.kubeconfig',
        '/etc/origin/node/pods/master-config.yaml',
    )

    kube_cmd = "kubectl"

    def setup(self):
        # Rather than loading the config file, use the OCP command directly
        # that wraps kubectl, so we don't have to manually account for any
        # other changes the `oc` binary may implement
        if self.path_exists('/etc/origin/master/admin.kubeconfig'):
            self.kube_cmd = 'oc'
        self.resources.extend([
            'limitranges',
            'policies',
            'resourcequotas',
            'routes'
        ])
        self.global_resources.extend([
            'projects',
            'pvs'
        ])
        super().setup()


class UbuntuKubernetes(Kubernetes, UbuntuPlugin, DebianPlugin):

    packages = ('kubernetes',)

    files = (
        '/root/cdk/cdk_addons_kubectl_config',
        '/etc/kubernetes/admin.conf',
        '/var/snap/microk8s/current/credentials/client.config',
    )

    services = (
        # CDK
        'cdk.master.auth-webhook',
    )

    def setup(self):
        for _kconf in self.files:
            if self.path_exists(_kconf):
                self.kube_cmd += f" --kubeconfig={_kconf}"
                break

        for svc in self.services:
            self.add_journal(units=svc)

        if self.is_installed('microk8s'):
            self.kube_cmd = 'microk8s kubectl'

        self.config_files.extend([
            '/root/cdk/kubelet/config.yaml',
            '/root/cdk/audit/audit-policy.yaml'
        ])
        super().setup()


# vim: et ts=5 sw=4
