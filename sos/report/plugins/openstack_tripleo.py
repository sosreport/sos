# Copyright (C) 2020 Red Hat, Inc., Cedric Jeanneret <cjeanner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin
import re


class OpenStackTripleO(Plugin, IndependentPlugin):

    short_desc = 'Installation information from OpenStack Installer'

    plugin_name = 'openstack_tripleo'
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')
    packages = ('openstack-selinux',)

    def setup(self):
        # Notes: recursion is max 2 for container-puppet and tripleo-config
        # Those directories are present on all OpenStack nodes
        self.tripleo_log_paths = [
            '/var/log/paunch.log',
            '/var/lib/container-puppet/',
            '/var/lib/tripleo-config/',
            '/var/lib/tripleo/',
            '/etc/puppet/hieradata/'
        ]
        self.add_copy_spec(self.tripleo_log_paths)

    def postproc(self):
        # Ensures we do not leak passwords from the tripleo-config and
        # hieradata locations.
        # Other locations don't have sensitive data.
        secrets = r'(".*(key|password|pass|secret|database_connection))' \
                  r'([":\s]+)(.*[^"])([",]+)'
        rgxp = re.compile(secrets, re.IGNORECASE)

        for path in self.tripleo_log_paths:
            self.do_path_regex_sub(path, rgxp, r'\1\3*********\5')

# vim: set et ts=4 sw=4 :
