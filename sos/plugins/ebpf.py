# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import json


class Ebpf(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """eBPF tool
    """
    plugin_name = 'ebpf'
    profiles = ('system', 'kernel', 'network')

    def get_bpftool_prog_ids(self, prog_json):
        out = []
        try:
            prog_data = json.loads(prog_json)
        except Exception as e:
            self._log_info("Could not parse bpftool prog list as JSON: %s" % e)
            return out
        for item in range(len(prog_data)):
            if "id" in prog_data[item]:
                out.append(prog_data[item]["id"])
        return out

    def get_bpftool_map_ids(self, map_json):
        out = []
        try:
            map_data = json.loads(map_json)
        except Exception as e:
            self._log_info("Could not parse bpftool map list as JSON: %s" % e)
            return out
        for item in range(len(map_data)):
            if "id" in map_data[item]:
                out.append(map_data[item]["id"])
        return out

    def setup(self):
        # collect list of eBPF programs and maps and their dumps
        progs = self.collect_cmd_output("bpftool -j prog list")
        for prog_id in self.get_bpftool_prog_ids(progs['output']):
            for dumpcmd in ["xlated", "jited"]:
                self.add_cmd_output("bpftool prog dump %s id %s" %
                                    (dumpcmd, prog_id))

        maps = self.collect_cmd_output("bpftool -j map list")
        for map_id in self.get_bpftool_map_ids(maps['output']):
            self.add_cmd_output("bpftool map dump id %s" % map_id)

        self.add_cmd_output([
            # collect list of eBPF programs and maps and their dumps
            # in human readable form
            "bpftool prog list",
            "bpftool map list",
            # Iterate over all cgroups and list all attached programs
            "bpftool cgroup tree",
            # collect list of bpf program attachments in the kernel
            # networking subsystem
            "bpftool net list"
        ])

        # Capture list of bpf program attachments from namespaces
        ip_netns = self.exec_cmd("ip netns")
        cmd_prefix = "ip netns exec "
        if ip_netns['status'] == 0:
            out_ns = []
            for line in ip_netns['output'].splitlines():
                # If there's no namespaces, no need to continue
                if line.startswith("Object \"netns\" is unknown") \
                        or line.isspace() \
                        or line[:1].isspace():
                    continue
                out_ns.append(line.partition(' ')[0])
            for namespace in out_ns:
                ns_cmd_prefix = cmd_prefix + namespace + " "
                self.add_cmd_output(ns_cmd_prefix + "bpftool net list")

# vim: set et ts=4 sw=4 :
