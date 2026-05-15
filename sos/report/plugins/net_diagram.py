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
    """
    This plugin generates a visual network topology diagram (PNG) using
    Graphviz and generates ASCII. It maps relationships between physical NICs,
    Bonds, Bridges, Team devices, Tunnels, and Containers to help support
    engineers visualize complex network hierarchies.
    """

    plugin_name = 'net_diagram'
    profiles = ('network',)
    packages = ('graphviz', 'teamd', 'perl-Graph-Easy')

    def collect(self):
        # Header with tighter spacing for optimal layout
        dot_lines = [
            "digraph network {",
            "  rankdir=LR; overlap=false; splines=true;",
            "  nodesep=0.2; ranksep=0.5;",
            "  node [shape=box, style=filled, fontname=\"Arial\", "
            "fontsize=10];",
            "  edge [penwidth=1.5, color=\"#444444\"];"
        ]

        # 1. Map ALL IP Addresses
        ips = {}
        res_ips = self.exec_cmd("ip -br addr")
        if res_ips['status'] == 0:
            for line in res_ips['output'].splitlines():
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    ifname = parts[0].split('@')[0]
                    ips[ifname] = "\\n".join(parts[2:].pop().split())

        # 2. Identify ALL Routes across all tables
        res_routes = self.exec_cmd("ip route show table all")
        if res_routes['status'] == 0:
            seen_nodes = set()
            for line in res_routes['output'].splitlines():
                parts = line.split()
                if 'dev' not in parts:
                    continue

                dest = parts[0]
                if dest in ('local', 'broadcast', 'anycast', 'multicast'):
                    continue
                if dest.startswith(('ff00', '224.', '239.', '127.')):
                    continue

                iface = parts[parts.index('dev') + 1]
                tbl = parts[parts.index('table') + 1] if 'table' in parts \
                    else 'main'

                if 'via' in parts:
                    gw_ip = parts[parts.index('via') + 1]
                    gw_id = f"gw_{gw_ip.replace('.', '_')}"
                    if gw_id not in seen_nodes:
                        dot_lines.append(
                            f'  "{gw_id}" [label="Gateway\\n{gw_ip}", '
                            'shape=doubleoctagon, fillcolor="#eeeeee"];'
                        )
                        seen_nodes.add(gw_id)

                    r_lbl = f"to {dest}"
                    if tbl != 'main':
                        r_lbl += f"\\n(table: {tbl})"

                    r_col = "#e67e22" if tbl != 'main' else \
                            ("#27ae60" if dest == "default" else "#2980b9")

                    dot_lines.append(
                        f'  "{iface}" -> "{gw_id}" [label="{r_lbl}", '
                        f'color="{r_col}", style=dashed];'
                    )

                elif dest not in ('default', 'all'):
                    net_id = f"net_{dest.replace('.', '_').replace('/', '_')}"
                    if net_id not in seen_nodes:
                        dot_lines.append(
                            f'  "{net_id}" [label="Network\\n{dest}", '
                            'shape=ellipse, style=dotted, '
                            'fillcolor="#f9f9f9"];'
                        )
                        seen_nodes.add(net_id)
                    dot_lines.append(f'  "{iface}" -> "{net_id}" '
                                     f'[color="#7f8c8d", style=dotted];')

        # 3. Build Topology from Sysfs
        net_path = self.path_join("/sys", "class", "net")
        if self.path_exists(net_path):
            for iface in self.listdir(net_path):
                if iface in ('lo', 'bonding_masters'):
                    continue
                path = self.path_join(net_path, iface)

                if iface not in ips and not \
                   self.path_exists(self.path_join(path, "master")):
                    if not any(iface in line for line in dot_lines):
                        continue

                fill = "white"
                if any(x in iface for x in ("podman", "docker", "veth")):
                    fill = "#C3E6CB"
                elif self.path_exists(self.path_join(path, "bridge")):
                    fill = "#ADD8E6"
                elif self.path_exists(self.path_join(path, "bonding")):
                    fill = "#FFFFE0"
                elif self.path_exists(self.path_join(path, "device")):
                    fill = "#90EE90"
                elif self.path_exists(self.path_join(path, "tun_flags")):
                    fill = "#E1BEE7"

                label = f"<{iface}>"
                if iface in ips:
                    label += f"\\n{ips[iface]}"

                dot_lines.append(f'  "{iface}" [label="{label}", '
                                 f'fillcolor="{fill}"];')

                m_link = self.path_join(path, "master")
                if os.path.islink(m_link):
                    m_name = os.path.basename(os.readlink(m_link))
                    dot_lines.append(f'  "{iface}" -> "{m_name}" '
                                     f'[label="slave-of"];')

        dot_lines.append("}")

        with self.collection_file("network_topology.dot") as dotf:
            dotf.write("\n".join(dot_lines))
            dot_path = dotf.name

        png_path = dot_path.replace(".dot", ".png")
        self.exec_cmd(f"dot -Tpng {dot_path} -o {png_path}")

        # ASCII generation via bash - Conditional check for RHEL compatibility
        if self.exec_cmd("which graph-easy")['status'] == 0:
            txt_path = dot_path.replace(".dot", ".txt")
            cmd = (
                f"bash -c \"sed 's/shape=[a-z]*/shape=box/g' {dot_path} | "
                f"graph-easy --ascii > {txt_path}\""
            )
            self.exec_cmd(cmd)
        else:
            self._log_info("graph-easy tool not found; skipping ASCII output.")
