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

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
from os import path


class kubernetes(Plugin, RedHatPlugin):

    """Kubernetes plugin
    """

    # Red Hat Atomic Platform and OpenShift Enterprise use the
    # atomic-openshift-master package to provide kubernetes
    packages = ('kubernetes', 'atomic-openshift-master')
    files = ("/etc/origin/master/master-config.yaml",)

    option_list = [
        ("all", "use --all-namespaces for all kubectl commands",
            'fast', True),
        ("describe", "capture descriptions of all kube resources",
            'fast', True),
        ("podlogs", "capture logs for pods", 'slow', False),
    ]

    def check_is_master(self):
        if any([path.exists("/var/run/kubernetes/apiserver.key"),
                path.exists("/etc/origin/master/master-config.yaml")
                ]):
            return True
        else:
            return False

    def setup(self):
        self.add_copy_spec("/etc/kubernetes")
        self.add_copy_spec("/var/run/flannel")

        svcs = [
            'kubelet', 'kube-apiserver', 'kube-proxy', 'kube-scheduler',
            'kube-controller-manager'
        ]

        for svc in svcs:
            self.add_cmd_output("journalctl -u {}".format(svc))

        # We can only grab kubectl output from the master
        if self.check_is_master():
            kube_bin = "kubectl "
            if path.exists('/etc/origin/master/admin.kubeconfig'):
                kube_bin += "--config=/etc/origin/master/admin.kubeconfig"

            kube_get = "get -o json "
            if self.get_option('all'):
                kube_get += "--all-namespaces=true"

            for cmd in ['version', 'config view']:
                self.add_cmd_output("{} {}".format(kube_bin, cmd))

            resources = [
                'events', 'limitrange', 'pods', 'pvc', 'rc',
                'resourcequota', 'services'
            ]

            for res in resources:
                self.add_cmd_output(
                    "{} {} {}".format(
                        kube_bin,
                        kube_get,
                        res
                    )
                )
            resources.remove('events')
            # nodes and pvs are not namespaced, must pull separately
            self.add_cmd_output([
                "{} get -o json nodes".format(kube_bin),
                "{} get -o json pv".format(kube_bin)
                ]
            )

            if self.get_option('describe'):
                resources = resources + ['nodes', 'namespaces']
                for res in resources:
                    r = self.get_command_output(
                        "{} get {}".format(
                            kube_bin,
                            res
                        )
                    )
                    if r['status'] == 0:
                        k_list = [k.split()[0] for k in
                                  r['output'].splitlines()[1:]
                                  ]
                        for k in k_list:
                            self.add_cmd_output(
                                "{} describe {} {}".format(
                                    kube_bin,
                                    res,
                                    k
                                )
                            )

            if self.get_option('podlogs'):
                r = self.get_command_output(
                    "{} get pods".format(kube_bin)
                )
                if r['status'] == 0:
                    pods = [p.split()[0] for p in
                            r['output'].splitlines()[1:]
                            ]
                    for pod in pods:
                        self.add_cmd_output(
                            "{} logs {}".format(kube_bin, pod)
                        )

    def postproc(self):
        # First, clear sensitive data from the json output collected.
        # This will mask values when the "name" looks susceptible of
        # values worth obfuscating, i.e. if the name contains strings
        # like "pass", "pwd", "key" or "token"
        env_regexp = r'(?P<var>{\s*"name":\s*[^,]*' \
                     r'(pass|pwd|key|token|cred)[^,]*,\s*"value":)[^}]*'
        self.do_cmd_output_sub('kubectl', env_regexp,
                               r'\g<var> "********"', ignore_case=True)

        # Next, we need to handle the private keys and certs in describe
        # output that is not hit by the previous iteration.
        key_regexp = r'-----BEGIN ([A-Z]*).*?-----END ([A-Z].*)-----'
        self.do_cmd_output_sub('describe', key_regexp,
                               r'********', dotall=True)

# vim: et ts=5 sw=4
