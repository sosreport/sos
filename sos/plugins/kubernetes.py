# Copyright (C) 2014 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

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
from os import path


class kubernetes(Plugin, RedHatPlugin):

    """Kubernetes plugin
    """

    # Red Hat Atomic Platform and OpenShift Enterprise use the
    # atomic-openshift-master package to provide kubernetes
    packages = ('kubernetes', 'kubernetes-master', 'atomic-openshift-master')
    files = ("/etc/origin/master/master-config.yaml",)

    option_list = [
        ("all", "also collect --all-namespaces output separately",
            'fast', True),
        ("describe", "capture descriptions of all kube resources",
            'fast', True),
        ("podlogs", "capture logs for pods", 'slow', False),
    ]

    def check_is_master(self):
        if any([
            path.exists("/var/run/kubernetes/apiserver.key"),
            path.exists("/etc/origin/master/master-config.yaml")
        ]):
            return True
        return False

    def setup(self):
        self.add_copy_spec("/etc/kubernetes")
        self.add_copy_spec("/var/run/flannel")

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
        if self.check_is_master():
            kube_cmd = "kubectl "
            if path.exists('/etc/origin/master/admin.kubeconfig'):
                kube_cmd += "--config=/etc/origin/master/admin.kubeconfig"

            kube_get_cmd = "get -o json "
            for subcmd in ['version', 'config view']:
                self.add_cmd_output('%s %s' % (kube_cmd, subcmd))

            # get all namespaces in use
            kn = self.get_command_output('%s get namespaces' % kube_cmd)
            knsps = [n.split()[0] for n in kn['output'].splitlines()[1:] if n]

            resources = [
                'limitrange',
                'pods',
                'pvc',
                'rc',
                'resourcequota',
                'services'
            ]

            # nodes and pvs are not namespaced, must pull separately
            self.add_cmd_output([
                "{} get -o json nodes".format(kube_cmd),
                "{} get -o json pv".format(kube_cmd)
            ])

            for n in knsps:
                knsp = '--namespace=%s' % n
                k_cmd = '%s %s %s' % (kube_cmd, kube_get_cmd, knsp)

                self.add_cmd_output('%s events' % k_cmd)

                for res in resources:
                    self.add_cmd_output('%s %s' % (k_cmd, res))

                if self.get_option('describe'):
                    # need to drop json formatting for this
                    k_cmd = '%s get %s' % (kube_cmd, knsp)
                    for res in resources:
                        r = self.get_command_output(
                            '%s %s' % (k_cmd, res))
                        if r['status'] == 0:
                            k_list = [k.split()[0] for k in
                                      r['output'].splitlines()[1:]]
                            for k in k_list:
                                k_cmd = '%s %s' % (kube_cmd, knsp)
                                self.add_cmd_output(
                                    '%s describe %s %s' % (k_cmd, res, k))

                if self.get_option('podlogs'):
                    k_cmd = '%s get %s' % (kube_cmd, knsp)
                    r = self.get_command_output('%s get pods' % k_cmd)
                    if r['status'] == 0:
                        pods = [p.split()[0] for p in
                                r['output'].splitlines()[1:]]
                        for pod in pods:
                            self.add_cmd_output('%s logs %s' % (k_cmd, pod))

            if self.get_option('all'):
                k_cmd = '%s get --all-namespaces=true' % kube_cmd
                for res in resources:
                    self.add_cmd_output('%s %s' % (k_cmd, res))

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

# vim: et ts=5 sw=4
