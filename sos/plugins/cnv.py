# Copyright (C) 2018 Red Hat, Inc., Varun Khanna <vkhanna@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#
# This plugin collects information related to Container-native Virtualization
# add-on to OpenShift Container Platform.

from sos.plugins import Plugin, RedHatPlugin
import os.path


class CNV(Plugin, RedHatPlugin):

    ''' Container-native Virtualization '''

    plugin_name = 'cnv'
    profiles = ('openshift',)

    master_base_dir = "/etc/origin/master"
    master_cfg = os.path.join(master_base_dir, "master-config.yaml")

    # This plugin currently will also run on OCP with no cnv add-on.
    # In future, add a check to run the plugin only when cnv is installed
    files = (master_cfg,)

    option_list = [
        ("vm", "collect VM related data, usage: cnv.vm=<vmi name>", '', ""),
    ]

    def get_resc_ns(self, resc):
        out = []
        try:
            resc_ns_out = open(resc).read()
        except IOError:
            return out
        for line in resc_ns_out.splitlines():
            if line.startswith("NAMESPACE") \
                    or line.startswith("No resources found") \
                    or line.startswith("Error") \
                    or line.startswith("error"):
                pass
            else:
                out.append(line.split()[1] + " -n " + line.split()[0])
        return out

    def get_vm_ns(self, vms, option):
        out = []
        try:
            vms_ns_out = open(vms).read()
        except IOError:
            return out
        for line in vms_ns_out.splitlines():
            if line.startswith("NAMESPACE") \
                    or line.startswith("No resources found") \
                    or line.startswith("Error") \
                    or line.startswith("error"):
                pass
            else:
                if line.split()[1] == option:
                    out.append(line.split()[1] + " -n " + line.split()[0])
        return out

    def get_node_info(self, pods):
        out = ""
        try:
            node_out = open(pods).read()
        except IOError:
            return out
        for line in node_out.splitlines():
            if line.startswith("NAMESPACE") \
                    or line.startswith("No resources found") \
                    or line.startswith("Error") \
                    or line.startswith("error"):
                pass
            else:
                out = line.split()[7]
        return out

    def setup(self):
        oc_admin_cfg = os.path.join(self.master_base_dir, "admin.kubeconfig")
        oc_cmd = "%s --config=%s" % ("oc", oc_admin_cfg)

        all_dep = [
            "%s get deployment -l kubevirt.io "
            "--all-namespaces -o wide" % oc_cmd,
        ]
        all_svc = [
            "%s get service -l kubevirt.io "
            "--all-namespaces -o wide" % oc_cmd,
            "%s get service -l cdi.kubevirt.io "
            "--all-namespaces -o wide" % oc_cmd,
        ]
        all_pods = [
            "%s get pods -l kubevirt.io=virt-controller "
            "--all-namespaces -o wide" % oc_cmd,
            "%s get pods -l kubevirt.io=virt-api "
            "--all-namespaces -o wide" % oc_cmd,
            "%s get pods -l cdi.kubevirt.io "
            "--all-namespaces -o wide" % oc_cmd,
            "%s get pods -l app=containerized-data-importer "
            "--all-namespaces -o wide" % oc_cmd,
        ]
        all_stor = [
            "%s get pvc --all-namespaces -o wide" % oc_cmd,
        ]

        subcmds = [
            "nodes",
            "clusterroles",
            "clusterrolebinding",
            "serviceaccount --all-namespaces",
            "storageclass --all-namespaces",
            "pv --all-namespaces",
            "dv --all-namespaces",
        ]
        subcmds_dep = [
            "describe deployment",
        ]
        subcmds_svc = [
            "describe svc",
        ]
        subcmds_pods = [
            "describe pod",
            "logs",
        ]

        self.add_cmd_output(["%s version" % oc_cmd])
        self.add_cmd_output(["virtctl --kubeconfig %s version" % oc_admin_cfg])
        for s in subcmds:
            self.add_cmd_output(["%s " % oc_cmd + "get " + s])
        for dep in all_dep:
            for d in self.get_resc_ns(self.get_cmd_output_now(dep)):
                for s in subcmds_dep:
                    self.add_cmd_output(["%s " % oc_cmd + s + " " + d])
        for svc in all_svc:
            for sv in self.get_resc_ns(self.get_cmd_output_now(svc)):
                for s in subcmds_svc:
                    self.add_cmd_output(["%s " % oc_cmd + s + " " + sv])
        for pod in all_pods:
            for p in self.get_resc_ns(self.get_cmd_output_now(pod)):
                for s in subcmds_pods:
                    self.add_cmd_output(["%s " % oc_cmd + s + " " + p])
        for stor in all_stor:
            for pvc in self.get_resc_ns(self.get_cmd_output_now(stor)):
                self.add_cmd_output(["%s get pvc -o yaml " % oc_cmd + pvc])
        self.add_cmd_output("%s get vm --all-namespaces" % oc_cmd)
        vmis = self.get_cmd_output_now("%s get vmi --all-namespaces" % oc_cmd)

        if self.get_option("vm"):
            options = self.get_option("vm")
            if isinstance(options, bool):
                return

            subcmds_vm = [
                "describe vm",
                "describe vmi",
                "get vm -o yaml",
                "get vmi -o yaml",
            ]
            node_pods = [
                "%s get pods -l kubevirt.io=virt-handler "
                "--all-namespaces -o wide" % oc_cmd,
                "%s get pods -l app=multus "
                "--all-namespaces -o wide" % oc_cmd,
                "%s get pods -l app=ovs-cni "
                "--all-namespaces -o wide" % oc_cmd,
                "%s get pods -l app=ovs "
                "--all-namespaces -o wide" % oc_cmd,
                "%s get pods -l app=sdn "
                "--all-namespaces -o wide" % oc_cmd,
            ]

            for vm in self.get_vm_ns(vmis, self.get_option("vm")):
                for s in subcmds_vm:
                    self.add_cmd_output(["%s " % oc_cmd + s + " " + vm])
                getvmi = "%s get vmi " % oc_cmd + vm + " --show-labels"
                lbl_ext = self.call_ext_prog(getvmi)
                vmi_l = ""
                if lbl_ext['status'] != 0:
                    return
                for line in lbl_ext['output'].splitlines():
                    if line.split()[0] == vm.split()[0]:
                        for l in line.split()[2].split(','):
                            if vm.split()[0] in l:
                                vmi_l = "-l " + l + " --all-namespaces -o wide"
                p_ln = self.get_cmd_output_now("%s get pods " % oc_cmd + vmi_l)
                for pod in self.get_resc_ns(p_ln):
                    for s in subcmds_pods:
                        self.add_cmd_output(["%s " % oc_cmd + s + " " + pod])
                    exc = "%s " % oc_cmd + "exec " + pod + " -- virsh dumpxml "
                    dmn = vm.split()[2] + "_" + vm.split()[0]
                    self.add_cmd_output([exc + dmn])
                node = self.get_node_info(p_ln)
                vm_pods = []
                for pod in node_pods:
                    node_pod_ext = self.call_ext_prog(pod)
                    if node_pod_ext['status'] == 0:
                        for line in node_pod_ext['output'].splitlines():
                            if line.startswith("NAMESPACE") \
                                    or line.startswith("No resources found") \
                                    or line.startswith("Error") \
                                    or line.startswith("error"):
                                pass
                            else:
                                if line.split()[7] == node:
                                    p = line.split()[1]
                                    ns = " -n " + line.split()[0]
                                    vm_pods.append(p + ns)
                for pod in vm_pods:
                    for s in subcmds_pods:
                        self.add_cmd_output(["%s " % oc_cmd + s + " " + pod])
                    if pod.startswith("sdn"):
                        exc = "%s " % oc_cmd + "exec " + pod
                        self.add_cmd_output([exc + " -- ovs-vsctl show "])
                        self.add_cmd_output([exc + " -- ip -o a "])
                        self.add_cmd_output([exc + " -- ip route "])

    def postproc(self):
        # Clear sensitive data from collected outputs
        # This will mask values when the "name" looks susceptible of
        # values worth obfuscating, i.e. if the name contains strings
        # like "pass", "key" or "ssh" etc.

        env_regexp = r'(?P<var>(pass|PASS|key|KEY|ssh|SSH' \
                     r'|TOKEN|CRED|SECRET|token|cred|secret).*)'
        self.do_cmd_output_sub('oc', env_regexp, "********")

# vim: set et ts=4 sw=4 :
