# Copyright (C) 2020 Red Hat, Inc., Cedric Jeanneret <cjeanner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import re


class OpenStackTripleO(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Fetch installation informations from OpenStack Installer
    """

    plugin_name = 'openstack_tripleo'
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')
    packages = ('openstack-selinux',)

    def setup(self):
        # Notes: recursion is max 2 for container-puppet and tripleo-config
        # Those directories are present on all OpenStack nodes
        self.add_copy_spec([
            '/var/log/paunch.log',
            '/var/lib/container-puppet/',
            '/var/lib/tripleo-config/',
            '/etc/puppet/hieradata/'
        ])

    def postproc(self):
        # Ensures we do not leak passwords from the tripleo-config and
        # hieradata locations.
        # Other locations don't have sensitive data.
        secrets = r'(".*(key|password|pass|secret|database_connection))' \
                  r'([":\s]+)(.*[^"])([",]+)'
        rgxp = re.compile(secrets, re.IGNORECASE)

        self.do_path_regex_sub('/var/lib/tripleo-config/',
                               rgxp, r'\1\3*********\5')
        self.do_path_regex_sub('/etc/puppet/hieradata/',
                               rgxp, r'\1\3*********\5')


# vim: set et ts=4 sw=4 :
