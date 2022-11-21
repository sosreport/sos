# Copyright (C) 2022 Red Hat, Inc.

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


MISTRAL_DIRECTORIES = [
        '/var/log/mistral/',
        '/var/lib/mistral/',
        ]
MISTRAL_LOGS = [
        '/var/log/mistral/*.log',
        '/var/lib/mistral/*/*.log',
        ]


class OpenStackMistral(Plugin, RedHatPlugin):
    '''Gather Mistral directories content, both data from /var/lib/mistral
    and its log from /var/log/mistral if it exists (older OSP).
    The data also embed logs for the ansible runs launched via the service,
    meaning we'll be able to properly debug failures therein. The rest of the
    data are the generated environment files, also really useful in order
    to debug an issue at deploy or day-2 operations.
    We filter out on the presence of any "mistral" related container on the
    host - usually the Undercloud presents mistral_engine, mistral_executor
    and mistral_api.
    '''

    short_desc = 'OpenStack Mistral'

    plugin_name = "openstack_mistral"
    profiles = ('openstack', 'openstack_undercloud')
    containers = ('.*mistral_engine',)

    def setup(self):
        if self.get_option('all_log'):
            self.add_copy_spec(MISTRAL_DIRECTORIES)
        else:
            self.add_copy_spec(MISTRAL_LOGS)

# vim: set et ts=4 sw=4 :
