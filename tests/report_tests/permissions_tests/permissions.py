# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Permissions(Plugin, IndependentPlugin):
    """Fake plugin for testing permission preservation"""

    plugin_name = 'permissions'
    short_desc = 'fake plugin to test permission preservation'

    def setup(self):
        self.add_copy_spec('/etc/no_perms_file.conf')
        self.add_copy_spec('/var/log/some_perms_file.log')
        self.add_copy_spec('/var/tmp/permissions-test')
