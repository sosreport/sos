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
import json
import os
from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)


KUBE_PACKAGES = (
    'kubelet',
    'kubernetes',
)

KUBE_SVCS = (
    'kubelet',
    'kube-apiserver',
    'kube-proxy',
    'kube-scheduler',
    'kube-controller-manager',
)

KUBECONFIGS = (
    '/etc/kubernetes/admin.conf',
)


class Kubernetes(Plugin):

    short_desc = 'Kubernetes container orchestration platform'

    plugin_name = "kubernetes"
    profiles = ('container',)
    plugin_timeout = 1200

    config_files = [
        "/etc/kubernetes",
        "/run/flannel",
        "/var/lib/kubelet/config.yaml",
        "/var/lib/kubelet/kubeadm-flags.env",
        "/var/lib/kubelet/*_manager_state",
    ]
    forbidden_paths = [
        "/etc/kubernetes/pki",
    ]
    kube_system_logs = [
        "/var/log/pods/kube-system_etcd-*",
        "/var/log/pods/kube-system_kube-apiserver-*",
        "/var/log/pods/kube-system_kube-controller-manager-*",
        "/var/log/pods/kube-system_kube-scheduler-*",
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
        'clusterrolebindings',
        'limitranges',
        'resourcequotas',
    ]

    # these are not namespaced, must pull separately.
    global_resources = [
        'sc',
        'pv',
        'roles',
        'rolebindings',
    ]

    option_list = [
        PluginOpt('all', default=False,
                  desc='collect all namespace output separately'),
        PluginOpt('describe', default=False,
                  desc='collect describe output of all resources'),
        PluginOpt('kubelogs', default=False,
                  desc='copy some kube-system pod logs without using the API'),
        PluginOpt('podlogs', default=False,
                  desc='capture stdout/stderr logs from pods using the API'),
        PluginOpt('podlogs-filter', default='', val_type=str,
                  desc='only collect logs from pods matching this pattern')
    ]

    kube_cmd = "kubectl"

    def set_kubeconfig(self):
        if os.environ.get('KUBECONFIG'):
            return
        for _kconf in self.files:
            if self.path_exists(_kconf):
                self.kube_cmd += f" --kubeconfig={_kconf}"
                break

    def check_is_master(self):
        """ Check if this is the master node """
        return any(self.path_exists(f) for f in self.files)

    def setup(self):
        self.add_copy_spec(self.config_files)

        self.add_forbidden_path(self.forbidden_paths)

        if self.get_option('kubelogs'):
            self.add_copy_spec(self.kube_system_logs)

        self.add_env_var([
            'KUBECONFIG',
            'KUBERNETES_HTTP_PROXY',
            'KUBERNETES_HTTPS_PROXY',
            'KUBERNETES_NO_PROXY',
        ])

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
            knsp = f'--namespace={nspace}'
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
                self._get_pod_logs(knsp)

    def _get_pod_logs(self, namespace):
        k_cmd = f'{self.kube_cmd} get -o json {namespace}'
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
                            f'{self.kube_cmd} {namespace} logs '
                            f'{pod_name} -c {cont_name}',
                            subdir=_subdir
                        )
                if "initContainers" in pod["spec"]:
                    for cont in pod["spec"]["initContainers"]:
                        pod_name = pod["metadata"]["name"]
                        cont_name = cont["name"]
                        self.add_cmd_output(
                            f'{self.kube_cmd} {namespace} logs '
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

        pathexp = fr'^({"|".join(self.config_files)})'
        self.do_file_private_sub(pathexp)

        # clear base64 encoded PEM from kubeconfigs files
        regexp = r'LS0tLS1CRUdJ[A-Za-z0-9+/=]+'
        subst = '***** SCRUBBED BASE64 PEM *****'
        pathexp = fr'^({"|".join(list(self.files)+self.config_files)})'
        self.do_path_regex_sub(pathexp, regexp, subst)


class RedHatKubernetes(Kubernetes, RedHatPlugin):

    packages = KUBE_PACKAGES

    files = KUBECONFIGS

    services = KUBE_SVCS

    def check_enabled(self):
        # do not run at the same time as the openshift plugin
        if self.is_installed("openshift-hyperkube"):
            return False
        return super().check_enabled()

    def setup(self):
        self.set_kubeconfig()
        super().setup()


class UbuntuKubernetes(Kubernetes, UbuntuPlugin, DebianPlugin):

    packages = KUBE_PACKAGES + (
        'k8s',
    )

    files = KUBECONFIGS + (
        '/root/cdk/cdk_addons_kubectl_config',
        '/var/snap/microk8s/current/credentials/client.config',
    )

    services = KUBE_SVCS + (
        'snap.kubelet.daemon',
        'snap.kube-apiserver.daemon',
        'snap.kube-proxy.daemon',
        'snap.kube-scheduler.daemon',
        'snap.kube-controller-manager.daemon',
        # CDK
        'cdk.master.auth-webhook',
    )

    def setup(self):
        self.set_kubeconfig()

        if self.is_installed('microk8s'):
            self.kube_cmd = 'microk8s kubectl'
        elif self.is_installed('k8s'):
            self.kube_cmd = 'k8s kubectl'
            self._canonical_kubernetes()

        self.config_files.extend([
            '/root/cdk/kubelet/config.yaml',
            '/root/cdk/audit/audit-policy.yaml',
        ])
        super().setup()

    def _canonical_kubernetes(self):
        k8s_units = ['snap.k8s.containerd.service',
                     'snap.k8s.etcd.service',
                     'snap.k8s.k8sd.service',
                     'snap.k8s.kube-apiserver.service',
                     'snap.k8s.kube-controller-manager.service',
                     'snap.k8s.kube-proxy.service',
                     'snap.k8s.kube-scheduler.service',
                     'snap.k8s.kubelet.service']
        self.add_journal(units=k8s_units)

        k8s_cmd = "k8s"
        k8s_common = "/var/snap/k8s/common"

        k8s_subcmds = [
            'status',
            'get',
        ]

        self.add_copy_spec([
            f"{k8s_common}/args",
            f"{k8s_common}/var/lib/k8s-dqlite/info.yaml",
            f"{k8s_common}/var/lib/k8s-dqlite/cluster.yaml",
            f"{k8s_common}/var/lib/k8sd/state/truststore/k8s.yaml",
            f"{k8s_common}/var/lib/k8sd/state/database/info.yaml",
            f"{k8s_common}/var/lib/k8sd/state/database/cluster.yaml",
            f"{k8s_common}/var/lib/k8sd/state/daemon.yaml",
        ])

        self.add_cmd_output([
            f"{k8s_cmd} {subcmd}" for subcmd in k8s_subcmds
        ])

    def postproc(self):
        super().postproc()

        self.do_file_private_sub(
            "/var/snap/k8s/common/var/lib/k8sd/state/truststore/k8s.yaml")


# vim: et ts=5 sw=4
