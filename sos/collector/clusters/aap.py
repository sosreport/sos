# Copyright (C) 2025 Red Hat Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import configparser
import json
import requests
from sos.utilities import TIMEOUT_DEFAULT
from sos.collector.clusters import Cluster


class aap(Cluster):
    """
    This cluster profile is for Ansible Automation Platform clusters.

    By default, all nodes in the cluster will be returned for collection.
    The list of nodes can be obtained via one of the following options:
    - Using the option 'inventory', the user can provide an inventory file
      with the list of instances.

    - Using the option 'api-url', the user can point to an API where sos
      can request the list of instances via an HTTP request.

    If none of these options are provided, the list of nodes will be
    obtained by calling 'awx-manage list_instances'.
    The last two options will provide an incomplete list of instances
    while the first one, the inventory file, will provide a full list.
    """

    cluster_name = 'Ansible Automation Platform Cluster'
    sos_plugins = [
        'aap_controller',
        'aap_eda',
        'aap_gateway',
        'aap_hub',
        'aap_receptor',
        'containers_common',
    ]

    commands = ('awx-manage',)

    option_list = [
        ('inventory', '', 'Inventory file provided by the user'),
        ('api-url', '', 'Ansible API URL to access list of instances')
    ]

    def parse_inventory_file(self, inventory):
        """
        Parse an inventory file provided by the user on the
        command line via the option 'inventory=<file>'.
        The format of this file is INI, where keys can have
        no value, and there's no default section in the file.
        We'll work with a list of node types explicitly
        but in the future we may want to make this list dynamic.
        """
        nodes = []
        node_types = (
            'automationcontroller',
            'automationedacontroller',
            'automationgateway',
            'automationhub',
            'database',
            'execution_nodes',
            'redis',
        )

        try:
            config = configparser.ConfigParser(
                allow_no_value=True,
                default_section=""
            )
            with open(inventory, 'r', encoding='utf-8') as inv:
                config.read_file(inv)
                nodes = [
                        node[0] for section in node_types for node in
                        config.items(section)
                ]
        except IOError as e:
            self.log_error(
                        f"Error while reading inventory file: {e}"
            )
        return nodes

    def parse_awx_manage_command(self, cmd_output):

        self.nodes = [
            line.split()[0].strip()
            for line in cmd_output.splitlines()
            if line.strip() and not line.startswith('[')
        ]

        return self.nodes

    def get_and_parse_inventory_from_api(self, url):
        """
        API URLs that provide list of instances
        will return a json object, and the list of
        hosts will be under the section 'results',
        with a tag 'hostname' for each instance
        """

        headers = {"Content-Type": "application/json"}
        res = None
        try:
            res = requests.get(
                               url=url,
                               headers=headers,
                               timeout=TIMEOUT_DEFAULT
            )
        except requests.HTTPError as e:
            self.log_error("HTTP request failed "
                           "while attempting to acquire the tokens."
                           f"Error returned was {res.status_code} : {e}")

        inventory = json.load(res.json())
        self.nodes = [section["hostname"] for section in inventory["results"]]

        return self.nodes

    def get_nodes(self):
        self.nodes = []
        if inv_file := self.get_option('inventory'):
            return self.parse_inventory_file(inv_file)

        if json_inv := self.get_option('api-url'):
            return self.get_and_parse_inventory_from_api(json_inv)

        # In case we didn't receive an inventory file
        # or an API URL, we'll fall back to get the list of
        # instances via the awx-manage command.
        awx_out = self.exec_primary_cmd(
            'awx-manage list_instances',
            need_root=True
        )
        if not awx_out['status'] == 0:
            self.log_error(
                "Could not enumerate nodes via awx-manage: "
                f"{awx_out['output']}"
            )
            return None
        return self.parse_awx_manage_command(awx_out['output'])


# vim: set et ts=4 sw=4 :
