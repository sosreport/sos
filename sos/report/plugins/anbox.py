# Copyright (C) 2026 Canonical Ltd.,
# Leah Goldberg <leah.goldberg@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Anbox(Plugin, IndependentPlugin):
    """
    Collects diagnostic information for Anbox.
    """

    short_desc = "Anbox/Anbox Cloud diagnostics"

    plugin_name = "anbox"
    profiles = ("container", "system")
    packages = ('anbox-cloud-appliance',)

    services = (
        "snap.anbox-cloud-appliance.ams",
        "snap.anbox-cloud-appliance.dashboard",
        "snap.anbox-cloud-appliance.daemon",
        "snap.anbox-cloud-appliance.stream-gateway",
        "snap.anbox-cloud-appliance.stream-agent",
        "snap.anbox-cloud-appliance.nats-server",
        "snap.anbox-cloud-appliance.coturn",
        "snap.anbox-cloud-appliance.openfga",
    )

    option_list = [
        PluginOpt('collectdb', default=False,
                  desc='Collect Anbox database file'),
    ]

    def setup(self):

        self.add_cmd_output([
            "amc addon list",
            "amc application list",
            "amc auth group list",
            "amc auth identity list",
            "amc auth permissions list",
            "amc config show",  # may have sensitive data
            "amc image list",
            "amc info",  # may have sensitive data
            "amc node list",
        ])

        try:
            # Get all AMC instances (JSON)
            result = self.exec_cmd("amc list --format json")

            try:
                instances = json.loads(result["output"])
            except Exception:
                self._log_error("Failed to parse amc list JSON output")
                return

            for inst in instances:
                inst_id = inst.get("id")

                # Skip invalid entries
                if not inst_id:
                    continue

                try:
                    # Instance summary
                    self.add_cmd_output(f"amc show {inst_id}")

                    # Get instance details for parsing stored logs
                    show_result = self.exec_cmd(
                        f"amc show {inst_id} --format json"
                    )

                    try:
                        show_data = json.loads(show_result["output"])
                    except Exception:
                        self._log_error(
                            f"Failed to parse amc show JSON for {inst_id}"
                        )
                        continue

                    logs = show_data.get("stored_logs", [])

                    # Collect all stored logs for instance
                    for log in logs:
                        self.add_cmd_output(
                            f"amc show-log {inst_id} {log}"
                        )

                except Exception as inst_err:
                    # Per-instance failure (continue processing others)
                    self._log_error(
                        f"Failed instance {inst_id}: {inst_err}"
                    )

        except Exception as e:
            # Global failure (AMC unavailable / broken output)
            self._log_error(
                f"Failed to retrieve Anbox instances: {e}"
            )

        # Collect DB files if requested
        if self.get_option("collectdb"):
            self.add_copy_spec([
                "/var/snap/anbox-cloud-appliance",
            ])

    def postproc(self):

        self.do_cmd_output_sub(
            "amc config show",
            r"(?i)(\s*.*(?:fingerprint|token|secret|password|key)\s*:\s*)(.*)",
            r"\1******"
        )

        self.do_cmd_output_sub(
            "amc info",
            r"(?i)(\s*.*(?:fingerprint|token|secret|password|key)\s*:\s*)(.*)",
            r"\1******"
        )
# vim: set et ts=4 sw=4 :
