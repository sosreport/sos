# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Atd(Plugin, IndependentPlugin):

    short_desc = 'At job scheduler'

    plugin_name = 'atd'
    profiles = ('system',)

    packages = ('at',)
    files = ('/etc/at.deny', '/etc/at.allow')
    services = ('atd',)

    def setup(self):
        self.add_copy_spec([
            '/etc/at.allow',
            '/etc/at.deny',
            '/etc/sysconfig/atd',
            '/etc/default/atd',
        ])

        # Queued jobs under /var/spool/at are complete shell scripts
        # carrying the submitting user's environment, so their contents
        # are not collected. A listing still shows which jobs are
        # pending, their queue, ownership and submission time.
        self.add_dir_listing('/var/spool/at', recursive=True,
                             tags='at_spool')

        self.add_cmd_output('atq', tags='atq')

# vim: set et ts=4 sw=4 :
