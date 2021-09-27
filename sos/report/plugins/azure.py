# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin, RedHatPlugin
import os


class Azure(Plugin, UbuntuPlugin):

    short_desc = 'Microsoft Azure client'

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
            "/sys/module/hv_storvsc/parameters/storvsc_ringbuffer_size",
            "/var/lib/AzureEnhancedMonitor"
        ])

        # Adds all files under /var/log/azure to the sosreport
        # os.walk is used because /var/log/azure is used by multiple Azure
        # extensions and there is no standard log filename format
        limit = self.get_option("log_size")

        for path, subdirs, files in os.walk("/var/log/azure"):
            for name in files:
                self.add_copy_spec(self.path_join(path, name), sizelimit=limit)

        self.add_cmd_output((
            'curl -s -H Metadata:true '
            '"http://169.254.169.254/metadata/instance/compute?'
            'api-version=2019-11-01"'
        ), suggest_filename='instance_metadata.json')


class RedHatAzure(Azure, RedHatPlugin):

    def setup(self):
        super(RedHatAzure, self).setup()

        if self.path_isfile('/etc/yum.repos.d/rh-cloud.repo'):
            curl_cmd = ('curl -s -m 5 -vvv '
                        'https://rhui-%s.microsoft.com/pulp/repos/%s')
            self.add_cmd_output([
                curl_cmd % ('1', 'microsoft-azure-rhel7'),
                curl_cmd % ('2', 'microsoft-azure-rhel7'),
                curl_cmd % ('3', 'microsoft-azure-rhel7')
            ])

        crt_path = '/etc/pki/rhui/product/content.crt'
        if self.path_isfile(crt_path):
            self.add_cmd_output([
                'openssl x509 -noout -text -in ' + crt_path
            ])

# vim: set et ts=4 sw=4 :
