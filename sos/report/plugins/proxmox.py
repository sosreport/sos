# Copyright (C) 2024 ORNESS/Ditrit Drien Breton <drien.breton@orness.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json

from sos.report.plugins import Plugin, DebianPlugin, PluginOpt


class Proxmox(Plugin, DebianPlugin):
    """
    This plugin will capture information about the system's
    Proxmox Virtualization Environment.

    It will collect information about the cluster, nodes, pools and
    storage from the Proxmox API.
    """
    short_desc = 'Proxmox cluster information'

    plugin_name = 'proxmox'
    packages = ('proxmox-ve',)

    option_list = [
        PluginOpt('output-formats',
                  desc='List of output formats to use '
                       'for the commands separated by ":".',
                  default='text',
                  ),
    ]

    def setup(self):
        output_formats = self.get_option('output-formats').split(':')

        commands = [
            'cluster/resources',
            'cluster/config/nodes',
            'cluster/options',
            'nodes/:id/status',
            'nodes/:id/storage',
            'nodes/:id/network',
            'pools',
            'storage',
            'storage/:sid',
            'cluster/ceph/status',
            'cluster/ceph/metadata',
            'cluster/ceph/flags',
        ]

        cmd_paths = []

        for command in commands:
            cmd_paths.extend(self.build_cmd_paths(command))

        self.add_cmd_output([
            f"pvesh get {cmd} {'--noborder' if format == 'text' else ''} "
            f"--output-format {format}"
            for cmd in cmd_paths
            for format in output_formats
        ])

    def build_cmd_paths(self, base_path):
        """
        Build command paths,
        replacing dynamic attributes with data from the API

        :param base_path: The base path to build from
        :type base_path: str

        :return: A list of paths
        """
        parts = base_path.split('/')
        paths = []

        id_index = next((i for i, part in enumerate(parts)
                         if part.startswith(':')), None)

        if id_index is not None:
            path = "/".join(parts[:id_index])
            trailing_path = "/".join(parts[id_index + 1:])

            results = self.exec_cmd(f'pvesh ls {path} --output-format json')

            if results["status"] == 0:
                children = json.loads(results["output"])
                for child in children:
                    paths.extend(
                        self.build_cmd_paths(
                            f"{path}/{child['name']}/{trailing_path}"
                        )
                    )

        else:
            paths.append('/'.join(parts))
        return paths

# vim: set et ts=4 sw=4 :
