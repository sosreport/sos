# Copyright (C) 2026 Harshith Hari <ghari@redhat.com>
# License: GPLv2

import os
import subprocess
from sos.report.plugins import Plugin, RedHatPlugin


class NetDiagram(Plugin, RedHatPlugin):
    """
    CEE-Grade Network Topology Visualizer.
    Generates a DOT graph and PNG image of the network hierarchy.
    """

    plugin_name = 'net_diagram'
    profiles = ('network',)
    packages = ('graphviz', 'teamd')

    def setup(self):
        # 1. Initial DOT Graph Header
        dot_lines = [
            "digraph network {",
            "  rankdir=LR; overlap=false; splines=true;",
            "  node [shape=box, style=filled, fontname=\"Arial\", "
            "fontsize=10];",
            "  edge [penwidth=2, color=\"#444444\"];"
        ]

        # 2. Capture IPs using standard subprocess
        ips = {}
        try:
            out = subprocess.check_output(
                ["ip", "-br", "addr"], encoding='utf-8'
            )
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    ips[parts[0]] = "\\n".join(parts[2:])
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        net_path = "/sys/class/net/"
        if not os.path.exists(net_path):
            return

        # 3. Process Interfaces and Relationships
        for iface in os.listdir(net_path):
            if iface in ('lo', 'bonding_masters'):
                continue

            path = os.path.join(net_path, iface)
            fill = "white"

            if os.path.exists(os.path.join(path, "bridge")):
                fill = "#ADD8E6"
            elif os.path.exists(os.path.join(path, "bonding")):
                fill = "#FFFFE0"
            elif os.path.islink(os.path.join(path, "device")):
                fill = "#90EE90"
            elif "team" in iface:
                fill = "#FADBD8"

            label = f"{iface}"
            if iface in ips:
                label += f"\\n{ips[iface]}"

            dot_lines.append(
                f'  "{iface}" [label="{label}", fillcolor="{fill}"];'
            )

            master_link = os.path.join(path, "master")
            if os.path.islink(master_link):
                m_name = os.path.basename(os.readlink(master_link))
                dot_lines.append(
                    f'  "{iface}" -> "{m_name}" [label="master"];'
                )

            proc_bond = f"/proc/net/bonding/{iface}"
            if os.path.exists(proc_bond):
                try:
                    with open(proc_bond, 'r') as f:
                        for line in f:
                            if "Slave Interface:" in line:
                                slave = line.split(":")[1].strip()
                                dot_lines.append(
                                    f'  "{slave}" -> "{iface}" '
                                    f'[style=bold, color=blue];'
                                )
                except (IOError, OSError):
                    pass

        # 4. Gateway Detection
        try:
            route_out = subprocess.check_output(
                ["ip", "route", "show"], encoding='utf-8'
            )
            for line in route_out.splitlines():
                if "default via" in line:
                    p = line.split()
                    gw_ip = p[p.index("via") + 1]
                    gw_dev = p[p.index("dev") + 1]
                    dot_lines.append(
                        f'  "gw" [label="GW\\n{gw_ip}", shape=doublecircle, '
                        f'fillcolor="#98FB98"];'
                    )
                    dot_lines.append(
                        f'  "{gw_dev}" -> "gw" [color=red, style=dashed, '
                        f'label="default"];'
                    )
                    break
        except (subprocess.SubprocessError, ValueError, IndexError):
            pass

        dot_lines.append("}")
        dot_str = "\n".join(dot_lines)

        # 5. Save and Render (Using the safe add_string_as_file)
        self.add_string_as_file(dot_str, "topology.dot")

        # Create temporary files in /tmp with fixed names for rendering
        tmp_dot = "/tmp/sos_net.dot"
        tmp_png = "/tmp/sos_net.png"

        try:
            with open(tmp_dot, "w") as f:
                f.write(dot_str)
            # Use subprocess to run graphviz
            subprocess.run(
                ["dot", "-Tpng", tmp_dot, "-o", tmp_png], check=True
            )
            # Pull the PNG into the report
            self.add_copy_spec(tmp_png)
        except (subprocess.SubprocessError, IOError):
            pass

    def postproc(self):
        # Cleanup the /tmp files after SOS finishes
        for f in ["/tmp/sos_net.dot", "/tmp/sos_net.png"]:
            if os.path.exists(f):
                os.remove(f)
