# Copyright (C) 2020 Red Hat, Inc., Cedric Jeanneret <cjeanner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


# Notes:
# - The Validation Framework is, for now, linked to openstack and tripleo
# - Since the intent is to open it to other product (we can validate anything)
#   this plugin has a generic name.
# - The Framework is targeted at Red Hat products, at least for now.
class ValidationFramework(Plugin, RedHatPlugin):

    short_desc = 'Logs provided by the Validation Framework'

    plugin_name = 'validation_framework'
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')
    packages = ('tripleo-validations',)

    def setup(self):
        self.add_copy_spec('/var/log/validations/')

    def postproc(self):
        # Use a generic match in order to clean things up.
        # It is not expected to get any secrets in here, but we'd better
        # ensure it's clean.
        secrets = r'(".*(key|password|pass|secret|database_connection))' \
                  r'([":\s]+)(.*[^"])([",]+)'

        self.do_path_regex_sub('/var/log/validations/',
                               secrets, r'\1\3*********\5')

# vim: set et ts=4 sw=4 :
