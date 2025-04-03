# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest


class JujuBasicTest(StageOneReportTest):
    """Ensure that a basic execution runs as expected with simple deployment.

    :avocado: tags=sunbeam
    """

    sos_cmd = '-v -o juju'
    arch = ['x86_64']

    ubuntu_only = True

    def test_unit_agent_conf_collected(self):
        self.assertFileCollected('/var/lib/juju/agents/machine-0/agent.conf')
        self.assertFileCollected('/var/log/juju/machine-0.log')

#    def test_unit_commands_collected(self):
#        cmds_to_check = [
#            'juju_engine_report',
#            'juju_goroutines',
#            'juju_heap_profile',
#            'juju_leases',
#            'juju_metrics',
#            'juju_pubsub_report',
#            'juju_presence_report',
#            'juju_statepool_report',
#            'juju_statetracker_report',
#            'juju_unit_status',
#        ]
#
#        for the_cmd in cmds_to_check:
#            self.assertFileCollected(f'sos_commands/juju/{the_cmd}')

    def test_unit_agent_conf_cert_scrubbed(self):
        file = '/var/lib/juju/agents/machine-0/agent.conf'

        check_cert_scrub = [
            "cacert",
            "controllercert",
        ]
        for cert in check_cert_scrub:
            self.assertFileHasContent(
                file, f'{cert}: |\n  -----SCRUBBED CERTIFICATE-----')

    def test_unit_agent_conf_private_cert_scrubbed(self):
        file = '/var/lib/juju/agents/machine-0/agent.conf'
        check_priv_key = [
            "controllerkey",
            "caprivatekey",
        ]
        for priv in check_priv_key:
            self.assertFileHasContent(
                file, f'{priv}: |\n  -----SCRUBBED PRIVATE KEY-----')

    def test_unit_agent_conf_private_cert_rsa_scrubbed(self):
        file = '/var/lib/juju/agents/machine-0/agent.conf'
        check_priv_rsa_key = [
            "systemidentity",
        ]

        for priv_rsa in check_priv_rsa_key:
            self.assertFileHasContent(
                file, f'{priv_rsa}: |\n  -----SCRUBBED RSA PRIVATE KEY-----')

    def test_unit_agent_conf_secrets_scrubbed(self):
        file = '/var/lib/juju/agents/machine-0/agent.conf'

        check_key_scrub = [
            "sharedsecret",
            "apipassword",
            "oldpassword",
            "statepassword",
        ]

        for key in check_key_scrub:
            self.assertFileHasContent(file, rf'{key}: \*\*\*\*\*\*\*\*\*')

# vim: et ts=4 sw=4
