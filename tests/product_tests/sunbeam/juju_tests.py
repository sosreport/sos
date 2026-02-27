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

    agent_conf = "/var/lib/juju/agents/machine-0/agent.conf"

    def test_unit_agent_conf_collected(self):
        self.assertFileCollected(self.agent_conf)
        self.assertFileCollected('/var/log/juju/machine-0.log')

    def test_unit_retrospect_commands_collected(self):
        cmds_to_check = [
            'juju_engine_report',
            'juju_goroutines',
            'juju_heap_profile',
            'juju_metrics',
            'juju_pubsub_report',
            'juju_presence_report',
            'juju_statepool_report',
            'juju_statetracker_report',
            'juju_unit_status',
        ]

        for the_cmd in cmds_to_check:
            self.assertFileCollected(f'sos_commands/juju/{the_cmd}')

    def test_unit_agent_conf_cert_scrubbed(self):
        check_cert_scrub = [
            "cacert",
        ]

        for cert in check_cert_scrub:
            self.assertFileHasContent(
                self.agent_conf,
                f'{cert}: |\n  -----SCRUBBED CERTIFICATE-----'
            )

    def test_unit_agent_conf_secrets_scrubbed(self):
        check_key_scrub = [
            "apipassword",
            "oldpassword",
        ]

        for key in check_key_scrub:
            self.assertFileHasContent(
                self.agent_conf, rf'{key}: \*\*\*\*\*\*\*\*\*')

# vim: et ts=4 sw=4
