# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class MigrationResults(Plugin, RedHatPlugin):

    short_desc = 'Information about conversions and upgrades'

    plugin_name = 'migration_results'
    profiles = ('system',)

    files = ('/etc/migration-results',)

# vim: et ts=4 sw=4
