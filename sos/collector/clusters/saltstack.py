# Copyright Red Hat 2022, Trevor Benson <trevor.benson@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
from shlex import quote
from sos.collector.clusters import Cluster


class saltstack(Cluster):
    """
    The saltstack cluster profile is intended to be used on saltstack
    clusters (Salt Project).
    """

    cluster_name = "Saltstack"
    packages = ("salt-master",)
    sos_plugins = ["saltmaster"]
    strict_node_list = True
    option_list = [
        ("compound", "", "Filter node list to those matching compound"),
        ("glob", "", "Filter node list to those matching glob pattern"),
        ("grain", "", "Filter node list to those with matching grain"),
        ("minion_id_unresolvable", False, "Returns the FQDN grain of each"
         " minion in the node list when the minion ID is not a hostname."),
        ("nodegroup", "", "Filter node list to those matching nodegroup"),
        ("pillar", "", "Filter node list to those with matching pillar"),
        ("subnet", "", "Filter node list to those in subnet"),
    ]
    targeted = False

    node_cmd = "salt-run --out=pprint manage.status"

    def _parse_manage_status(self, output: str) -> list:
        nodes = []
        salt_json_output = json.loads(output.replace("'", '"'))
        for _, value in salt_json_output.items():
            nodes.extend(value)
        return nodes

    def _get_hostnames_from_grain(self, manage_status: dict) -> list:
        hostnames = []
        fqdn_cmd = "salt --out=newline_values_only {minion} grains.get fqdn"
        for status, minions in manage_status.items():
            if status == "down":
                self.log_warn(f"Node(s) {minions} are status down.")
                hostnames.extend(minions)
            else:
                for minion in minions:
                    node_cmd = fqdn_cmd.format(minion=minion)
                    hostnames.append(
                        self.exec_primary_cmd(node_cmd)["output"].strip()
                    )
        return hostnames

    def _get_nodes(self) -> list:
        res = self.exec_primary_cmd(self.node_cmd)
        if res["status"] != 0:
            raise Exception("Node enumeration did not return usable output")
        if self.get_option("minion_id_unresolvable"):
            status = json.loads(res["output"].replace("'", '"'))
            return self._get_hostnames_from_grain(status)
        return self._parse_manage_status(res["output"])

    def get_nodes(self):
        # Default to all online nodes
        for option in self.option_list:
            if option[0] != "minion_id_unresolvable":
                opt = self.get_option(option[0])
                if opt:
                    self.node_cmd += f" tgt={quote(opt)} tgt_type={option[0]}"
                    break
        return self._get_nodes()


# vim: set et ts=4 sw=4 :
