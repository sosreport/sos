# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


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
            self.add_copy_spec(self.HA_LOG_GLOB)

        # Add run-time status
        self.add_cmd_output([
            'hosted-engine --vm-status',
            'hosted-engine --check-liveliness',
        ])


# vim: expandtab tabstop=4 shiftwidth=4
