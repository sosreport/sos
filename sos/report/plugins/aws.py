# Copyright (C) 2025, Javier Blanco <javier@jblanco.es>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Aws(Plugin, IndependentPlugin):

    short_desc = 'AWS EC2 instance metadata'

    plugin_name = 'aws'
    profiles = ('virt',)

    def _is_ec2(self):
        try:
            with open('/sys/devices/virtual/dmi/id/sys_vendor',
                      encoding='utf-8') as f:
                return 'Amazon' in f.read()
        except FileNotFoundError:
            return False

    # Called by sos to determine if the plugin will run
    def check_enabled(self):
        return self._is_ec2()

    def setup(self):
        if not self._is_ec2():
            self.soslog.info(
                "Not an EC2 instance; skipping AWS metadata collection")
            return

        # Using IMDSv2 if possible, if not, going IMDSv1
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html

        # Try to get an IMDSv2 token
        token_url = 'http://169.254.169.254/latest/api/token'
        token_cmd = [
            'curl',
            '-sS',
            '-X',
            'PUT',
            '-H',
            'X-aws-ec2-metadata-token-ttl-seconds: 21600',
            token_url]

        try:
            token = self.exec_cmd(token_cmd, timeout=1)
        except Exception:
            token = ''

        # Add header only if token retrieval succeeded
        token_header = []

        if token:
            token_header = ['-H', f'X-aws-ec2-metadata-token: {token}']

        # Issue each metadata request individually
        meta_url = (
            'http://169.254.169.254/latest/meta-data/'
            'hostname'
        )
        self.add_cmd_output(
            ['curl', '-sS'] + token_header + [meta_url],
            suggest_filename='aws_metadata_hostname.txt'
        )

        meta_url = (
            'http://169.254.169.254/latest/meta-data/'
            'instance-id'
        )
        self.add_cmd_output(
            ['curl', '-sS'] + token_header + [meta_url],
            suggest_filename='aws_metadata_instance-id.txt'
        )

        meta_url = (
            'http://169.254.169.254/latest/meta-data/'
            'instance-life-cycle'
        )
        self.add_cmd_output(
            ['curl', '-sS'] + token_header + [meta_url],
            suggest_filename='aws_metadata_instance-life-cycle.txt'
        )

        meta_url = (
            'http://169.254.169.254/latest/meta-data/'
            'instance-type'
        )
        self.add_cmd_output(
            ['curl', '-sS'] + token_header + [meta_url],
            suggest_filename='aws_metadata_instance-type.txt'
        )

        meta_url = (
            'http://169.254.169.254/latest/meta-data/'
            'placement/availability-zone-id'
        )
        self.add_cmd_output(
            ['curl', '-sS'] + token_header + [meta_url],
            suggest_filename='aws_metadata_availability-zone-id.txt'
        )

        # Those metadata entries do not include any sensitive information.
        # No need to mask any data.

# vim: set et ts=4 sw=4 :
