# Copyright (C) 2023 Red Hat, Inc., Roberto Alfieri <ralfieri@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OpenStackEDPM(Plugin, RedHatPlugin):

    short_desc = 'Installation information from OpenStack EDPM deployment'

    plugin_name = 'openstack_edpm'
    profiles = ('openstack', 'openstack_edpm')
    services = ('edpm-container-shutdown')
    edpm_log_paths = []

    def setup(self):
        # Notes: recursion is max 2 for edpm-config
        # Those directories are present on all OpenStack nodes
        self.edpm_log_paths = [
            '/var/lib/edpm-config/'
        ]
        self.add_copy_spec(self.edpm_log_paths)

    def postproc(self):
        # Ensures we do not leak passwords from the edpm related locations
        # Other locations don't have sensitive data.
        regexp = r'(".*(key|password|pass|secret|database_connection))' \
                 r'([":\s]+)(.*[^"])([",]+)'
        for path in self.edpm_log_paths:
            self.do_path_regex_sub(path, regexp, r'\1\3*********\5')

# vim: set et ts=4 sw=4 :
