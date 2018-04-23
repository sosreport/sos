# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
from sos.plugins import Plugin, UbuntuPlugin, RedHatPlugin

class Azure(Plugin, UbuntuPlugin):
    """ Microsoft Azure client
    """

    plugin_name = 'azure'
    profiles = ('virt',)
    packages = ('WALinuxAgent',)

    def setup(self):
        self.add_copy_spec([
            "/var/log/waagent*",
            "/var/lib/cloud",
            "/etc/default/kv-kvp-daemon-init",
            "/etc/waagent.conf",
            "/sys/module/hv_netvsc/parameters/ring_size",
            "/sys/module/hv_storvsc/parameters/storvsc_ringbuffer_size"
        ])

        # Adds all files under /var/log/azure to the sosreport
        # os.walk is used here because /var/log/azure is used by multiple Microsoft Azure extensions
        # and there is no standard log filename format
        limit = self.get_option("log_size")

        for path, subdirs, files in os.walk("/var/log/azure"):
            for name in files:
                self.add_copy_spec(os.path.join(path, name), sizelimit=limit)

        self.add_cmd_output((
            'curl -s -H Metadata:true '
            '"http://169.254.169.254/metadata/instance?'
            'api-version=2017-08-01"'
        ), suggest_filename='instance_metadata.json')


class RedHatAzure(Azure, RedHatPlugin):

    def setup(self):
        super(RedHatAzure, self).setup()

        if os.path.isfile('/etc/yum.repos.d/rh-cloud.repo'):
            curl_cmd = ('curl -s -m 5 -vvv '
                        'https://rhui-%s.microsoft.com/pulp/repos/%s')
            self.add_cmd_output([
                curl_cmd % ('1', 'microsoft-azure-rhel7'),
                curl_cmd % ('2', 'microsoft-azure-rhel7'),
                curl_cmd % ('3', 'microsoft-azure-rhel7')
            ])

        crt_path = '/etc/pki/rhui/product/content.crt'
        if os.path.isfile(crt_path):
            self.add_cmd_output([
                'openssl x509 -noout -text -in ' + crt_path
            ])

# vim: set et ts=4 sw=4 :
