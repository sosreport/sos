# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.collector.clusters import Cluster
from setuptools._vendor.packaging import version
from xml.etree import ElementTree


class pacemaker(Cluster):

    cluster_name = 'Pacemaker High Availability Cluster Manager'
    sos_plugins = ['pacemaker']
    packages = ('pacemaker',)
    strict_node_list = True
    option_list = [
        ('online', True, 'Collect nodes listed as online'),
        ('offline', True, 'Collect nodes listed as offline'),
        ('only-corosync', False, 'Only use corosync.conf to enumerate nodes')
    ]

    def get_nodes(self):
        self.nodes = []
        # try crm_mon first
        try:
            if not self.get_option('only-corosync'):
                try:
                    self.get_nodes_from_crm()
                except Exception as err:
                    self.log_warn("Falling back to sourcing corosync.conf. "
                                  "Could not parse crm_mon output: %s" % err)
            if not self.nodes:
                # fallback to corosync.conf, in case the node we're inspecting
                # is offline from the cluster
                self.get_nodes_from_corosync()
        except Exception as err:
            self.log_error("Could not determine nodes from cluster: %s" % err)

        _shorts = [n for n in self.nodes if '.' not in n]
        if _shorts:
            self.log_warn(
                "WARNING: Node addresses '%s' may not resolve locally if you "
                "are not running on a node in the cluster. Try using option "
                "'-c pacemaker.only-corosync' if these connections fail."
                % ','.join(_shorts)
            )
        return self.nodes

    def get_nodes_from_crm(self):
        """
        Try to parse crm_mon output for node list and status.
        """
        xmlopt = '--output-as=xml'
        # older pacemaker had a different option for xml output
        _ver = self.exec_primary_cmd('crm_mon --version')
        if _ver['status'] == 0:
            cver = _ver['output'].split()[1].split('-')[0]
            if not version.parse(cver) > version.parse('2.0.3'):
                xmlopt = '--as-xml'
        else:
            return
        _out = self.exec_primary_cmd(
            "crm_mon --one-shot --inactive %s" % xmlopt,
            need_root=True
        )
        if _out['status'] == 0:
            self.parse_crm_xml(_out['output'])

    def parse_crm_xml(self, xmlstring):
        """
        Parse the xml output string provided by crm_mon
        """
        _xml = ElementTree.fromstring(xmlstring)
        nodes = _xml.find('nodes')
        for node in nodes:
            _node = node.attrib
            if self.get_option('online') and _node['online'] == 'true':
                self.nodes.append(_node['name'])
            elif self.get_option('offline') and _node['online'] == 'false':
                self.nodes.append(_node['name'])

    def get_nodes_from_corosync(self):
        """
        As a fallback measure, read corosync.conf to get the node list. Note
        that this prevents us from separating online nodes from offline nodes.
        """
        self.log_warn("WARNING: unable to distinguish online nodes from "
                      "offline nodes when sourcing from corosync.conf")
        cc = self.primary.read_file('/etc/corosync/corosync.conf')
        nodes = re.findall(r'((\sring0_addr:)(.*))', cc)
        for node in nodes:
            self.nodes.append(node[-1].strip())

# vim: set et ts=4 sw=4 :
