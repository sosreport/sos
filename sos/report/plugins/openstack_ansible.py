# Copyright (C) 2017 Major Hayden <major@mhtx.net>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class OpenStackAnsible(Plugin, IndependentPlugin):

    short_desc = 'OpenStack-Ansible'

    plugin_name = "openstack_ansible"
    profiles = ('openstack',)
    files = ('/etc/openstack_deploy/',)

    def setup(self):
        """Gathering the contents of the report."""
        self.add_copy_spec([
            "/etc/openstack_deploy/",
            "/etc/openstack-release",
            "/etc/rpc_deploy/",
            "/etc/rpc-release"
        ])

    def postproc(self):
        """Remove sensitive keys and passwords from YAML files."""
        secrets_files = [
            "/etc/openstack_deploy/user_secrets.yml",
            "/etc/rpc_deploy/user_secrets.yml"
        ]
        regexp = r"(?m)^\s*#*([\w_]*:\s*).*"
        for secrets_file in secrets_files:
            self.do_path_regex_sub(
                secrets_file,
                regexp,
                r"\1*********")
