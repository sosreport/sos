# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest


class K8sBasicTest(StageOneReportTest):
    """Ensure that a basic execution runs as expected with simple deployment.

    :avocado: tags=sunbeam
    """

    sos_cmd = '-v -o kubernetes'
    arch = ['x86_64']

    ubuntu_only = True

    k8s_cmd = "k8s"

    def test_k8s_config_collected(self):
        k8s_common = "/var/snap/k8s/common"

        k8s_files = [
            f"{k8s_common}/args",
            f"{k8s_common}/var/lib/k8s-dqlite/info.yaml",
            f"{k8s_common}/var/lib/k8s-dqlite/cluster.yaml",
            f"{k8s_common}/var/lib/k8sd/state/truststore/k8s.yaml",
            f"{k8s_common}/var/lib/k8sd/state/database/info.yaml",
            f"{k8s_common}/var/lib/k8sd/state/database/cluster.yaml",
            f"{k8s_common}/var/lib/k8sd/state/daemon.yaml",
        ]

        for file in k8s_files:
            self.assertFileCollected(file)

    def test_k8s_cmd_ran(self):
        ran_cmds = [
            "status",
            "get",
        ]
        for cmd_run in ran_cmds:
            self.assertFileCollected(
                f'sos_commands/kubernetes/{self.k8s_cmd}_{cmd_run}')

    def test_kubectl_cmd_ran(self):
        kube_cmd = f"{self.k8s_cmd}_kubectl"

        ran_cmds = [
            'config_view',
            'get_--all-namespaces_true_clusterrolebindings',
            'get_--all-namespaces_true_clusterroles',
            'get_--all-namespaces_true_configmaps',
            'get_--all-namespaces_true_cronjobs',
            'get_--all-namespaces_true_daemonsets',
            'get_--all-namespaces_true_deployments',
            'get_--all-namespaces_true_endpoints',
            'get_--all-namespaces_true_events',
            'get_--all-namespaces_true_ingresses',
            'get_--all-namespaces_true_jobs',
            'get_--all-namespaces_true_limitranges',
            'get_--all-namespaces_true_pods',
            'get_--all-namespaces_true_pvc',
            'get_--all-namespaces_true_replicasets',
            'get_--all-namespaces_true_resourcequotas',
            'get_--all-namespaces_true_secrets',
            'get_--all-namespaces_true_serviceaccounts',
            'get_--all-namespaces_true_services',
            'get_--all-namespaces_true_statefulsets',
            'get_--raw_.metrics',
            'get_-o_json_nodes',
            'get_namespaces',
            'get_nodes',
            'get_pv',
            'get_rolebindings',
            'get_roles',
            'get_sc',
            'version',
        ]

        for cmd_run in ran_cmds:
            self.assertFileCollected(
                'sos_commands/kubernetes/cluster-info/'
                f'{kube_cmd}_{cmd_run}')


# vim: et ts=4 sw=4
