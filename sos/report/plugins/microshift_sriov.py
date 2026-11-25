# Copyright (C) 2026 Pablo Acevedo <pacevedo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class MicroshiftSriov(Plugin, RedHatPlugin):
    """This plugin collects configuration and runtime state for the SR-IOV
    Network Operator shipped with MicroShift 4.x through the optional
    ``microshift-sriov`` RPM.

    The operator's custom resources (the ``sriovnetwork.openshift.io`` API
    group) are namespaced in the ``sriov-network-operator`` namespace. That
    namespace is outside the ``openshift-*``/``kube-*`` set inspected by
    default by the ``microshift`` plugin, so neither the custom resources nor
    the operator pod logs are otherwise collected. In addition to those API
    resources this plugin collects host-side SR-IOV state (virtual function
    counts, eswitch mode and NIC driver/firmware versions) that is required to
    triage dataplane issues but that no API object exposes.
    """

    short_desc = 'MicroShift SR-IOV'
    plugin_name = 'microshift_sriov'
    packages = ('microshift-sriov',)
    profiles = ('microshift',)
    localhost_kubeconfig = '/var/lib/microshift/resources/kubeadmin/kubeconfig'

    # MicroShift ships the operator in this fixed namespace (see
    # assets/optional/sriov in the microshift tree); it is not user
    # configurable, unlike the OpenShift operator.
    namespace = 'sriov-network-operator'

    # All SR-IOV Network Operator custom resources are namespaced.
    sriov_resources = (
        'sriovoperatorconfigs',
        'sriovnetworknodestates',
        'sriovnetworknodepolicies',
        'sriovnetworks',
        'sriovibnetworks',
        'ovsnetworks',
        'sriovnetworkpoolconfigs',
    )

    option_list = [
        PluginOpt('kubeconfig', default=localhost_kubeconfig, val_type=str,
                  desc='Path to a locally available kubeconfig file'),
    ]

    def _get_sriov_resources(self):
        """Probe for the SR-IOV custom resources that are actually served by
        the API server, so that collection is a no-op for any resource whose
        CRD happens not to be installed (for example ``ovsnetworks`` only
        exists when the OVS hardware offload feature is in use).
        """
        _filtered_resources = []
        _kubeconfig = self.get_option('kubeconfig')
        for resource in self.sriov_resources:
            _resource = f'{resource}.sriovnetwork.openshift.io'
            res = self.exec_cmd(
                f"oc get --kubeconfig {_kubeconfig} -n {self.namespace} "
                f"{_resource}")
            if res['status'] == 0:
                _filtered_resources.append(_resource)
        return _filtered_resources

    def setup(self):
        """Collect host-side SR-IOV state unconditionally so that hardware
        problems remain visible even when the control plane is degraded, then
        inspect the operator namespace (pods, logs, events, configuration) and
        the SR-IOV custom resources from the API server when MicroShift is
        running.
        """
        # Host-side SR-IOV state not already covered by the 'networking'
        # plugin (which collects 'ip -d link', 'devlink dev info/port show'
        # and the per-device eswitch mode): virtual function counts and
        # per-VF driver binding. Generic lspci output is left to the 'pci'
        # plugin.
        self.add_copy_spec([
            '/sys/class/net/*/device/sriov_numvfs',
            '/sys/class/net/*/device/sriov_totalvfs',
            # Per-VF driver binding (DRIVER=) and PCI slot, which distinguish
            # vfio-pci (DPDK) VFs from kernel netdevice VFs. The 'pci' plugin
            # records the same via 'lspci -nnvvv', but only across all PCI
            # devices; here it is scoped to the SR-IOV virtual functions.
            '/sys/class/net/*/device/virtfn*/uevent',
        ])

        if not self.is_service_running('microshift'):
            return

        _kubeconfig = self.get_option('kubeconfig')
        _subdir = self.get_cmd_output_path(make=False)

        # Inspect the operator namespace. This collects the operator, config
        # daemon, device plugin and CNI pod definitions and their logs, plus
        # events and config maps (such as the device plugin configuration).
        self.add_cmd_output(
            f'oc adm inspect --kubeconfig {_kubeconfig} --dest-dir '
            f'{_subdir} ns/{self.namespace}',
            suggest_filename='inspect_sriov_namespace.log')

        # NetworkAttachmentDefinitions generated from SriovNetwork CRs. These
        # are created in the target workload namespaces (networkNamespace),
        # not the operator namespace, so collect them cluster-wide. They are
        # the link between the SR-IOV CRs and the pods that consume them.
        self.add_cmd_output(
            f'oc get --kubeconfig {_kubeconfig} '
            f'network-attachment-definitions.k8s.cni.cncf.io '
            f'--all-namespaces -o yaml',
            suggest_filename='network_attachment_definitions.yaml')

        # SR-IOV custom resources. These are namespaced but not part of the
        # resource set 'oc adm inspect ns/...' gathers, so inspect them
        # explicitly into the same destination directory.
        _resources = ",".join(self._get_sriov_resources())
        if _resources:
            self.add_cmd_output(
                f'oc adm inspect --kubeconfig {_kubeconfig} --dest-dir '
                f'{_subdir} -n {self.namespace} {_resources}',
                suggest_filename='inspect_sriov_resources.log')
