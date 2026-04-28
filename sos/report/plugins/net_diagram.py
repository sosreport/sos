# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#
# Copyright (C) 2026 Harshith Hari <harshithhari000111@gmail.com>

import os
from sos.report.plugins import Plugin, IndependentPlugin


class NetDiagram(Plugin, IndependentPlugin):
    """This plugin generates a visual network topology diagram (PNG) using
    Graphviz. It maps relationships between physical NICs, Bonds, Bridges,
    and Team devices to help support engineers visualize complex network
    hierarchies.
    """

    plugin_name = 'net_diagram'
    profiles = ('network',)
    packages = ('graphviz', 'teamd')

    def collect(self):
        dot_lines = [
            "digraph network {",
            "  rankdir=LR; overlap=false; splines=true;",
            "  node [shape=box, style=filled, fontname=\"Arial\", "
            "fontsize=10];",
            "  edge [penwidth=2, color=\"#444444\"];"
        ]

        # 1. Map IP Addresses with stacking logic
        ips = {}
        res = self.exec_cmd("ip -br addr")
        if res['status'] == 0:
            for line in res['output'].splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    ips[parts[0]] = "\\n".join(parts[2:])

        # 2. Identify Default Gateway and create a Cloud node
        res_gw = self.exec_cmd("ip route show default")
        if res_gw['status'] == 0 and res_gw['output']:
            parts = res_gw['output'].split()
            if 'via' in parts and 'dev' in parts:
                gw_ip = parts[parts.index('via') + 1]
                gw_dev = parts[parts.index('dev') + 1]
                dot_lines.append(
                    f'  "gateway" [label="Gateway\\n{gw_ip}", '
                    'shape=cloud, fillcolor="#f9f9f9"];'
                )
                dot_lines.append(
                    f'  "{gw_dev}" -> "gateway" [label="default route", '
                    'color="#27ae60", style=dashed];'
                )

        # 3. Build Topology from Sysfs relationships using Plugin API
        net_path = self.path_join("/sys", "class", "net")
        # Use self.path_exists and self.listdir for sysroot compliance
        if self.path_exists(net_path):
            for iface in self.listdir(net_path):
                if iface in ('lo', 'bonding_masters'):
                    continue

                path = self.path_join(net_path, iface)
                fill = "white"

                if self.path_exists(self.path_join(path, "bridge")):
                    fill = "#ADD8E6"
                elif self.path_exists(self.path_join(path, "bonding")):
                    fill = "#FFFFE0"
                elif self.path_exists(self.path_join(path, "device")):
                    fill = "#90EE90"
                elif "team" in iface:
                    fill = "#FADBD8"

                label = f"{iface}"
                if iface in ips:
                    label += f"\\n{ips[iface]}"

                dot_lines.append(
                    f'  "{iface}" [label="{label}", fillcolor="{fill}"];'
                )

                master_link = self.path_join(path, "master")
                # For readlink, we still use os as Plugin doesn't wrap it
                if os.path.islink(master_link):
                    m_name = os.path.basename(os.readlink(master_link))
                    dot_lines.append(
                        f'  "{iface}" -> "{m_name}" [label="master"];'
                    )

        dot_lines.append("}")

        with self.collection_file("network_topology.dot") as dotf:
            dotf.write("\n".join(dot_lines))
            dot_path = dotf.name

        png_path = dot_path.replace(".dot", ".png")
        self.exec_cmd(f"dot -Tpng {dot_path} -o {png_path}")
