# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import os
from sos.report.plugins import Plugin, UbuntuPlugin, RedHatPlugin


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

        # Adds all files under /var/log/azure to the sos report
        # os.walk is used because /var/log/azure is used by multiple Azure
        # extensions and there is no standard log filename format
        limit = self.get_option("log_size")

        for path, _, files in os.walk("/var/log/azure"):
            for name in files:
                self.add_copy_spec(self.path_join(path, name), sizelimit=limit)

        self.add_cmd_output((
            'curl -s -H Metadata:true --noproxy "*" '
            '"http://169.254.169.254/metadata/instance/compute?'
            'api-version=2023-07-01&format=json"'
        ), suggest_filename='instance_metadata.json')


class RedHatAzure(Azure, RedHatPlugin):

    def setup(self):
        super().setup()

        # RHUI repo files vary by RHEL version and offering:
        # rh-cloud.repo (RHEL 7), rh-cloud-base.repo, rh-cloud-eus.repo,
        # rh-cloud-ha.repo, rh-cloud-sap-ha.repo, rh-cloud-arm64.repo, etc.
        rhui_repos = glob.glob('/etc/yum.repos.d/rh-cloud*.repo')
        if rhui_repos:
            # RHUI 1/2/3 are retired; Azure Global now uses RHUI 4
            # https://learn.microsoft.com/en-us/azure/virtual-machines/
            # workloads/redhat/redhat-rhui
            self.add_cmd_output(
                'curl -s -m 5 -vvv https://rhui4-1.microsoft.com'
            )

            # Collect any hardcoded RHUI entries in /etc/hosts
            self.add_cmd_output(
                'grep -i rhui /etc/hosts',
                suggest_filename='rhui_etc_hosts'
            )

        # Certificate filenames vary by RHEL version and offering:
        # content.crt, content-base.crt, content-eus.crt,
        # content-base-ha.crt, content-base-sap-ha.crt, etc.
        crt_dir = '/etc/pki/rhui/product'
        for crt_path in glob.glob(f'{crt_dir}/*.crt'):
            self.add_cmd_output(
                f'openssl x509 -noout -text -in {crt_path}'
            )

# vim: set et ts=4 sw=4 :
