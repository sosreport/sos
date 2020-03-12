# Copyright (C) 2018 Amit Ghadge <amitg.b14@gmail.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import re


class Elastic(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """
    ElasticSearch service
    """
    plugin_name = 'elastic'
    profiles = ('services', )

    packages = ('elasticsearch',)

    def get_hostname_port(self, els_config_file):
        hostname = "localhost"
        port = "9200"
        try:
            with open(els_config_file) as fread:
                for line in fread:
                    network_host = re.search(r'(^network.host):(.*)', line)
                    network_port = re.search(r'(^http.port):(.*)', line)
                    if network_host and len(network_host.groups()) == 2:
                        hostname = network_host.groups()[-1].strip()
                        hostname = re.sub(r'"|\'', '', hostname)
                        continue
                    if network_port and len(network_port.groups()) == 2:
                        port = network_port.groups()[-1].strip()
        except Exception as e:
            self._log_info("Failed to parse %s: %s" % (els_config_file, e))
        return hostname, port

    def setup(self):
        els_config_file = "/etc/elasticsearch/elasticsearch.yml"
        self.add_copy_spec(els_config_file)

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/elasticsearch/*")
        else:
            self.add_copy_spec("/var/log/elasticsearch/elasticsearch.log")

        host, port = self.get_hostname_port(els_config_file)
        endpoint = host + ":" + port
        self.add_cmd_output([
                "curl -X GET '%s/_cluster/settings?pretty'" % endpoint,
                "curl -X GET '%s/_cluster/health?pretty'" % endpoint,
                "curl -X GET '%s/_cluster/stats?pretty'" % endpoint,
                "curl -X GET '%s/_cat/nodes?v'" % endpoint,
            ])

# vim: set et ts=4 sw=4 :
