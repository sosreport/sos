# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


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

    SETUP_LOG_GLOB = '/var/log/ovirt-hosted-engine-setup/*.log'
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
        ])

        all_setup_logs = glob.glob(self.SETUP_LOG_GLOB)
        all_setup_logs.sort(reverse=True)
        if len(all_setup_logs):
            # Add latest ovirt-hosted-engine-setup log file
            self.add_copy_spec(all_setup_logs[0])
        # Add older ovirt-hosted-engine-setup log files only if requested
        if self.get_option('all_logs'):
            self.add_copy_spec_limit(
                self.SETUP_LOG_GLOB,
                sizelimit=self.limit
            )

        self.add_copy_spec([
            '/var/log/ovirt-hosted-engine-ha/agent.log',
            '/var/log/ovirt-hosted-engine-ha/broker.log',
        ])
        # Add older ovirt-hosted-engine-ha log files only if requested
        if self.get_option('all_logs'):
            self.add_copy_spec_limit(
                self.HA_LOG_GLOB,
                sizelimit=self.limit,
            )

        # Add run-time status
        self.add_cmd_output([
            'hosted-engine --vm-status',
            'hosted-engine --check-liveliness',
        ])


# vim: expandtab tabstop=4 shiftwidth=4
