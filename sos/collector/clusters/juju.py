# Copyright (c) 2023 Canonical Ltd., Chi Wai Chan <chiwai.chan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging
import json
import re

from sos.collector.clusters import Cluster
from sos.utilities import sos_parse_version
from sos.utilities import sos_get_command_output


def _parse_option_string(strings=None):
    """Parse comma separated string."""
    if not strings:
        return []
    return [string.strip() for string in strings.split(",")]


def _get_index(model_name):
    """Helper function to get Index.

    The reason why we need Index defined in function is because currently
    the collector.__init__ will load all the classes in this module
    and also Index. This will cause bug because it think Index is
    Cluster type. Also We don't want to provide a customized
    filter to remove Index class.
    """

    class Index:
        """Index structure to help parse juju status output.

        Attributes apps, units and machines are dict which key
        is the app/unit/machine name
        and the value is list of targets which format are
        {model_name}:{machine_id}.
        """

        def __init__(self, model_name):
            self.model_name: str = model_name
            self.apps = {}
            self.units = {}
            self.machines = {}
            self.ui_log = logging.getLogger("sos")

        def add_principals(self, juju_status):
            """Adds principal units to index."""
            for app, app_info in juju_status["applications"].items():
                nodes = []
                units = app_info.get("units", {})
                for unit, unit_info in units.items():
                    machine = unit_info["machine"]
                    node = f"{self.model_name}:{machine}"
                    self.units[unit] = [node]
                    self.machines[machine] = [node]
                    nodes.append(node)

                self.apps[app] = nodes

        def add_subordinates(self, juju_status):
            """Add subordinates to index.

            Since subordinates does not have units they need to be
            manually added.
            """
            for app, app_info in juju_status["applications"].items():
                subordinate_to = app_info.get("subordinate-to", [])
                for parent in subordinate_to:
                    # If parent is missing
                    if not self.apps.get(parent):
                        self.ui_log.warning(
                            f"Principal charm {parent} is missing"
                        )
                        continue
                    self.apps[app].extend(self.apps[parent])

                    # If parent's units is missing
                    if "units" not in juju_status["applications"][parent]:
                        self.ui_log.warning(
                            f"Principal charm {parent} is missing units"
                        )
                        continue

                    units = juju_status["applications"][parent]["units"]
                    for _, unit_info in units.items():
                        node = f"{self.model_name}:{unit_info['machine']}"
                        for sub_key, _ in unit_info.get(
                            "subordinates", {}
                        ).items():
                            if sub_key.startswith(app + "/"):
                                self.units[sub_key] = [node]

        def add_machines(self, juju_status):
            """Add machines to index.

            If model does not have any applications it needs to be
            manually added.
            """
            for machine in juju_status["machines"].keys():
                node = f"{self.model_name}:{machine}"
                self.machines[machine] = [node]

    return Index(model_name)


class juju(Cluster):
    """
    The juju cluster profile is intended to be used on juju managed clouds.
    It"s assumed that `juju` is installed on the machine where `sos` is called,
    and that the juju user has superuser privilege to the current controller.

    By default, the sos reports will be collected from all the applications in
    the current model. If necessary, you can filter the nodes by models /
    applications / units / machines with cluster options.

    Example:

    sos collect --cluster-type juju -c "juju.models=sos" -c "juju.apps=a,b,c"

    """

    cmd = "juju"
    cluster_name = "Juju Managed Clouds"
    option_list = [
        ("apps", "", "Filter node list by apps (comma separated regex)."),
        ("units", "", "Filter node list by units (comma separated string)."),
        ("models", "", "Filter node list by models (comma separated string)."),
        (
            "machines",
            "",
            "Filter node list by machines (comma separated string).",
        ),
    ]

    def _cleanup_juju_output(self, output):
        """Remove leading characters before {."""
        return re.sub(r"(^[^{]*)(.*)", "\\2", output, 0, re.MULTILINE)

    def _get_model_info(self, model_name):
        """Parse juju status output and return target dict.

        Here are couple helper functions to parse the juju principals units,
        subordinate units and machines.
        """
        juju_status = self._execute_juju_status(model_name)

        index = _get_index(model_name=model_name)
        index.add_principals(juju_status)
        index.add_subordinates(juju_status)
        index.add_machines(juju_status)

        return index

    def _get_juju_version(self):
        """Grab the version of juju"""
        res = sos_get_command_output("juju version")
        return res['output']

    def _execute_juju_status(self, model_name):
        model_option = f"-m {model_name}" if model_name else ""
        format_option = "--format json"
        juju_version = self._get_juju_version()
        if sos_parse_version(juju_version) > sos_parse_version("3"):
            format_option += " --no-color"
        status_cmd = f"{self.cmd} status {model_option} {format_option}"
        res = self.exec_primary_cmd(status_cmd)
        if not res["status"] == 0:
            raise Exception(f"'{status_cmd}' returned error: {res['status']}")
        juju_json_output = self._cleanup_juju_output((res["output"]))

        juju_status = None
        juju_status = json.loads(juju_json_output)
        return juju_status

    def _filter_by_pattern(self, key, patterns, model_info):
        """Filter with regex match."""
        nodes = set()
        for pattern in patterns:
            for param, value in getattr(model_info, key).items():
                if re.match(pattern, param):
                    nodes.update(value or [])
        return nodes

    def _filter_by_fixed(self, key, patterns, model_info):
        """Filter with fixed match."""
        nodes = set()
        for pattern in patterns:
            for param, value in getattr(model_info, key).items():
                if pattern == param:
                    nodes.update(value or [])
        return nodes

    def set_transport_type(self):
        """Dynamically change transport to 'juju'."""
        return "juju"

    def get_nodes(self):
        """Get the machine numbers from `juju status`."""
        models = _parse_option_string(self.get_option("models"))
        apps = _parse_option_string(self.get_option("apps"))
        units = _parse_option_string(self.get_option("units"))
        machines = _parse_option_string(self.get_option("machines"))
        filters = {"apps": apps, "units": units, "machines": machines}

        # Return empty nodes if no model and filter provided.
        if not any(filters.values()) and not models:
            return []

        if not models:
            models = [""]  # use current model by default

        nodes = set()

        for model in models:
            model_info = self._get_model_info(model)
            for key, resource in filters.items():
                # Filter node by different policies
                if key == "apps":
                    _nodes = self._filter_by_pattern(key, resource, model_info)
                else:
                    _nodes = self._filter_by_fixed(key, resource, model_info)
                nodes.update(_nodes)

        return list(nodes)


# vim: set et ts=4 sw=4 :
