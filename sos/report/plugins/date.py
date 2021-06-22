# Copyright (C) 2018 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Date(Plugin, IndependentPlugin):

    short_desc = 'Basic system time information'

    plugin_name = 'date'

    def setup(self):

        self.add_cmd_output([
            'date',
            'date --utc',
            'hwclock'
        ])

        self.add_copy_spec([
            '/etc/localtime',
            '/etc/adjtime',
        ])

# vim: set et ts=4 sw=4 :
