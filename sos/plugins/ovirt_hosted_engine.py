# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>

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


import glob


from sos.plugins import Plugin, RedHatPlugin


class OvirtHostedEngine(Plugin, RedHatPlugin):
    """oVirt Hosted Engine"""

    packages = (
        'ovirt-hosted-engine-setup',
        'ovirt-hosted-engine-ha',
    )

    plugin_name = 'ovirt_hosted_engine'
    profiles = ('virt',)

    HA_LOG_GLOB = '/var/log/ovirt-hosted-engine-ha/*.log'

    def setup(self):
        self.limit = self.get_option('log_size')

        # Add configuration files
        # Collecting the whole directory since it may contain branding
        # configuration files or third party plugins configuration files
        self.add_copy_spec(['/etc/ovirt-hosted-engine-setup.env.d/'])

        self.add_copy_spec([
            '/etc/ovirt-hosted-engine/answers.conf',
            '/etc/ovirt-hosted-engine/hosted-engine.conf',
            '/etc/ovirt-hosted-engine/vm.conf',
            '/etc/ovirt-hosted-engine-ha/agent.conf',
            '/etc/ovirt-hosted-engine-ha/agent-log.conf',
            '/etc/ovirt-hosted-engine-ha/broker.conf',
            '/etc/ovirt-hosted-engine-ha/broker-log.conf',
            '/etc/ovirt-hosted-engine-ha/notifications/state_transition.txt',
            '/var/run/ovirt-hosted-engine-ha/vm.conf',
            '/var/lib/ovirt-hosted-engine-ha/broker.conf',
        ])

        self.add_copy_spec([
            '/var/log/ovirt-hosted-engine-setup',
            '/var/log/ovirt-hosted-engine-ha/agent.log',
            '/var/log/ovirt-hosted-engine-ha/broker.log',
        ])
        # Add older ovirt-hosted-engine-ha log files only if requested
        if self.get_option('all_logs'):
            self.add_copy_spec(
                self.HA_LOG_GLOB,
                sizelimit=self.limit,
            )

        # Add run-time status
        self.add_cmd_output([
            'hosted-engine --vm-status',
            'hosted-engine --check-liveliness',
        ])


# vim: expandtab tabstop=4 shiftwidth=4
