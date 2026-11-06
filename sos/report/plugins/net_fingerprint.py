# Copyright (c) 2026 Harshith <harshithhari000111@gmail.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import platform
import re
from sos.report.plugins import IndependentPlugin, Plugin


class NetFingerprint(Plugin, IndependentPlugin):
    """Captures canonical PCI network hardware, driver bindings, interface
    states, offloads, and kernel error logs into structured JSON and text.
    """

    short_desc = "Network and driver fingerprint for regression analysis"
    plugin_name = "net_fingerprint"
    profiles = ('network', 'hardware')

    def collect(self):
        """Parse source data via exec_cmd without duplicating command files,
        writing normalized regression artifacts using collection_file.
        """
        kernel_ver = platform.release()
        pci_nics = {}
        interfaces = {}
        fw_errors = []
        sysctl_core = {}

        # --- A. PCI Hardware & Drivers ---
        lspci_res = self.exec_cmd("lspci -nnk")
        lspci_out = ""
        if lspci_res and lspci_res.get("status") == 0:
            lspci_out = lspci_res.get("output", "")

        pci_pattern = (
            r"^([0-9a-fA-F:.]+)\s+(?:Ethernet|Network)\s+controller"
            r".*\[([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\]"
        )
        if lspci_out:
            cur_slot = None
            for line in lspci_out.splitlines():
                match = re.match(pci_pattern, line)
                if match:
                    cur_slot = match.group(1)
                    pci_nics[cur_slot] = {
                        "pci_id": match.group(2),
                        "driver": "NONE",
                        "modules": []
                    }
                    continue

                # An unindented line is the start of a non-NIC device entry
                if not line.startswith(("\t", " ")):
                    cur_slot = None
                    continue

                if cur_slot:
                    if "Kernel driver in use:" in line:
                        driver = line.split(":")[-1].strip()
                        pci_nics[cur_slot]["driver"] = driver
                    elif "Kernel modules:" in line:
                        mods = [
                            m.strip() for m in line.split(":")[-1].split(",")
                        ]
                        pci_nics[cur_slot]["modules"] = mods

        # --- B. Interface States and Addresses ---
        ip_link_res = self.exec_cmd("ip -d -j link show")
        ip_link_out = ""
        if ip_link_res and ip_link_res.get("status") == 0:
            ip_link_out = ip_link_res.get("output", "")

        if ip_link_out:
            try:
                for dev in json.loads(ip_link_out):
                    ifname = dev.get("ifname")
                    if ifname == "lo":
                        continue
                    interfaces[ifname] = {
                        "mac": dev.get("address", "").lower(),
                        "state": dev.get("operstate", "UNKNOWN"),
                        "flags": ",".join(dev.get("flags", [])),
                        "driver": "NONE",
                        "firmware": "NONE"
                    }
            except (json.JSONDecodeError, KeyError):
                pass

        if not interfaces:
            ip_link_fb = self.exec_cmd("ip -d link show")
            fb_out = ""
            if ip_link_fb and ip_link_fb.get("status") == 0:
                fb_out = ip_link_fb.get("output", "")
            if fb_out:
                cur_if = None
                for line in fb_out.splitlines():
                    dev_m = re.match(r"^\d+:\s+([^:@]+)", line)
                    if dev_m:
                        cur_if = dev_m.group(1).strip()
                        if cur_if != "lo":
                            is_up = "state UP" in line
                            interfaces[cur_if] = {
                                "mac": "",
                                "state": "UP" if is_up else "DOWN",
                                "flags": "",
                                "driver": "NONE",
                                "firmware": "NONE"
                            }
                    mac_m = re.search(r"link/\w+\s+([0-9a-f:]{17})", line)
                    if mac_m and cur_if and cur_if in interfaces:
                        interfaces[cur_if]["mac"] = mac_m.group(1).lower()

        # Query ethtool info per interface
        for iface in sorted(interfaces.keys()):
            ethtool_i = self.exec_cmd(f"ethtool -i {iface}")
            out = ""
            if ethtool_i and ethtool_i.get("status") == 0:
                out = ethtool_i.get("output", "")
            if out:
                for line in out.splitlines():
                    if line.startswith("driver:"):
                        val = line.split(":", 1)[1].strip()
                        interfaces[iface]["driver"] = val
                    elif line.startswith("firmware-version:"):
                        val = line.split(":", 1)[1].strip()
                        interfaces[iface]["firmware"] = val

        # --- C. Firmware Warnings/Errors (Debian, RHEL, Upstream) ---
        dmesg_res = self.exec_cmd("dmesg --level=err,warn -k")
        dmesg_out = ""
        if dmesg_res and dmesg_res.get("status") == 0:
            dmesg_out = dmesg_res.get("output", "")
        if dmesg_out:
            fw_patterns = [
                r"firmware:\s+failed\s+to\s+load\s+([^\s]+)",
                r"Direct\s+firmware\s+load\s+for\s+([^\s]+)\s+failed",
            ]
            for line in dmesg_out.splitlines():
                for pat in fw_patterns:
                    match = re.search(pat, line, re.IGNORECASE)
                    if match:
                        fw_name = match.group(1).strip()
                        fw_errors.append(f"{fw_name} -> {line.strip()}")
                        break

        # --- D. Core Network Sysctl Values ---
        sysctl_res = self.exec_cmd("sysctl -a --pattern '^net\\.'")
        sysctl_out = ""
        if sysctl_res and sysctl_res.get("status") == 0:
            sysctl_out = sysctl_res.get("output", "")
        if sysctl_out:
            watch_keys = [
                "net.ipv4.ip_forward",
                "net.ipv4.conf.all.rp_filter",
                "net.ipv4.conf.default.rp_filter",
                "net.bridge.bridge-nf-call-iptables"
            ]
            for line in sysctl_out.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k in watch_keys:
                        sysctl_core[k] = v.strip()

        # --- E. Write Artifacts using collection_file ---
        json_data = {
            "kernel": kernel_ver,
            "pci_nics": pci_nics,
            "interfaces": interfaces,
            "firmware_errors": fw_errors,
            "sysctl_core": sysctl_core
        }
        with self.collection_file("net_fingerprint.json") as jf:
            jf.write(json.dumps(json_data, indent=2))

        txt_lines = [
            f"KERNEL_RELEASE: {kernel_ver}",
            "",
            "[PCI_DEVICES_AND_DRIVERS]",
        ]
        for slot in sorted(pci_nics.keys()):
            dev = pci_nics[slot]
            mods = ",".join(dev["modules"]) if dev["modules"] else "none"
            txt_lines.append(
                f"PCI_SLOT={slot} ID=[{dev['pci_id']}] "
                f"DRIVER={dev['driver']} MODULES_AVAIL={mods}"
            )

        txt_lines.extend(["", "[NETWORK_INTERFACES]"])
        for ifname in sorted(interfaces.keys()):
            item = interfaces[ifname]
            txt_lines.append(
                f"IFACE={ifname} MAC={item['mac']} STATE={item['state']} "
                f"DRIVER={item['driver']} FW={item['firmware']} "
                f"FLAGS=[{item['flags']}]"
            )

        txt_lines.extend(["", "[CORE_SYSCTL]"])
        for k in sorted(sysctl_core.keys()):
            txt_lines.append(f"{k} = {sysctl_core[k]}")

        txt_lines.extend(["", "[FIRMWARE_ERRORS]"])
        if fw_errors:
            for err in sorted(fw_errors):
                txt_lines.append(f"MISSING_FW: {err}")
        else:
            txt_lines.append("NONE")

        with self.collection_file("net_fingerprint.txt") as tf:
            tf.write("\n".join(txt_lines) + "\n")
