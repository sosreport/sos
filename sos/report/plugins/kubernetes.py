# Copyright (C) 2014 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin
from fnmatch import translate
from os import path
import re


class Kubernetes(Plugin):
    """Kubernetes plugin
    """

    plugin_name = "kubernetes"
    profiles = ('container',)

    option_list = [
        ("all", "also collect all namespaces output separately",
            'slow', False),
        ("describe", "capture descriptions of all kube resources",
            'fast', False),
        ("podlogs", "capture logs for pods", 'slow', False),
        ("podlogs-filter", "only capture logs for pods matching this string",
            'fast', '')
    ]

    kube_cmd = "kubectl"

    def check_is_master(self):
        return any([path.exists(f) for f in self.files])

    def setup(self):
        self.add_copy_spec("/etc/kubernetes")
        self.add_copy_spec("/run/flannel")

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
            'kube-controller-manager'
        ]

        for svc in svcs:
            self.add_journal(units=svc)

        # We can only grab kubectl output from the master
        if not self.check_is_master():
            return

        kube_get_cmd = "get -o json "
        for subcmd in ['version', 'config view']:
            self.add_cmd_output('%s %s' % (self.kube_cmd, subcmd))

        # get all namespaces in use
        kn = self.collect_cmd_output('%s get namespaces' % self.kube_cmd)
        # namespace is the 1st word on line, until the line has spaces only
        kn_output = kn['output'].splitlines()[1:]
        knsps = [n.split()[0] for n in kn_output if n and len(n.split())]

        resources = [
            'deployments',
            'ingresses',
            'limitranges',
            'pods',
            'policies',
            'pvc',
            'rc',
            'resourcequotas',
            'routes',
            'services'
        ]

        # these are not namespaced, must pull separately.
        global_resources = [
            'namespaces',
            'projects',
            'pvs'
        ]
        self.add_cmd_output([
            "%s get %s" % (self.kube_cmd, res) for res in global_resources
        ])

        # Get detailed node information
        nodes = self.collect_cmd_output("%s get nodes" % self.kube_cmd)
        if nodes['status'] == 0:
            for line in nodes['output'].splitlines()[1:]:
                node = line.split()[0]
                self.add_cmd_output(
                    "%s describe node %s" % (self.kube_cmd, node),
                    subdir='nodes'
                )

        # Also collect master metrics
        self.add_cmd_output("%s get --raw /metrics" % self.kube_cmd)

        # CNV is not part of the base installation, but can be added
        if self.is_installed('kubevirt-virtctl'):
            resources.extend(['vms', 'vmis'])
            self.add_cmd_output('virtctl version')

        for n in knsps:
            knsp = '--namespace=%s' % n
            if self.get_option('all'):
                k_cmd = '%s %s %s' % (self.kube_cmd, kube_get_cmd, knsp)

                self.add_cmd_output('%s events' % k_cmd)

                for res in resources:
                    self.add_cmd_output('%s %s' % (k_cmd, res), subdir=res)

            if self.get_option('describe'):
                # need to drop json formatting for this
                k_cmd = '%s %s' % (self.kube_cmd, knsp)
                for res in resources:
                    r = self.exec_cmd('%s get %s' % (k_cmd, res))
                    if r['status'] == 0:
                        k_list = [k.split()[0] for k in
                                  r['output'].splitlines()[1:]]
                        for k in k_list:
                            k_cmd = '%s %s' % (self.kube_cmd, knsp)
                            self.add_cmd_output(
                                '%s describe %s %s' % (k_cmd, res, k),
                                subdir=res
                            )

            if self.get_option('podlogs'):
                k_cmd = '%s %s' % (self.kube_cmd, knsp)
                r = self.exec_cmd('%s get pods' % k_cmd)
                if r['status'] == 0:
                    pods = [p.split()[0] for p in
                            r['output'].splitlines()[1:]]
                    # allow shell-style regex
                    reg = (translate(self.get_option('podlogs-filter')) if
                           self.get_option('podlogs-filter') else None)
                    for pod in pods:
                        if reg and not re.match(reg, pod):
                            continue
                        self.add_cmd_output('%s logs %s' % (k_cmd, pod),
                                            subdir='pods')

        if not self.get_option('all'):
            k_cmd = '%s get --all-namespaces=true' % self.kube_cmd
            for res in resources:
                self.add_cmd_output('%s %s' % (k_cmd, res), subdir=res)

    def postproc(self):
        # First, clear sensitive data from the json output collected.
        # This will mask values when the "name" looks susceptible of
        # values worth obfuscating, i.e. if the name contains strings
        # like "pass", "pwd", "key" or "token"
        env_regexp = r'(?P<var>{\s*"name":\s*[^,]*' \
            r'(pass|pwd|key|token|cred|PASS|PWD|KEY)[^,]*,\s*"value":)[^}]*'
        self.do_cmd_output_sub('kubectl', env_regexp,
                               r'\g<var> "********"')

        # Next, we need to handle the private keys and certs in some
        # output that is not hit by the previous iteration.
        self.do_cmd_private_sub('kubectl')


class RedHatKubernetes(Kubernetes, RedHatPlugin):
    """Red Hat Kubernetes plugin
    """

    # OpenShift Container Platform uses the atomic-openshift-master package
    # to provide kubernetes
    packages = ('kubernetes', 'kubernetes-master', 'atomic-openshift-master')

    files = (
        '/etc/origin/master/admin.kubeconfig',
        '/etc/origin/node/pods/master-config.yaml',
    )

    kube_cmd = "kubectl"
    # Rather than loading the config file, use the OCP command directly that
    # wraps kubectl, so we don't have to manually account for any other changes
    # the `oc` binary may implement
    if path.exists('/etc/origin/master/admin.kubeconfig'):
        kube_cmd = 'oc'


class UbuntuKubernetes(Kubernetes, UbuntuPlugin):
    """Ubuntu Kubernetes plugin
    """

    packages = ('kubernetes',)

    files = ('/root/cdk/kubeproxyconfig',)

    kube_cmd = "kubectl --kubeconfig=/root/cdk/kubeproxyconfig"

# vim: et ts=5 sw=4
