# megacli.py
# Copyright (C) 2007-2014 Red Hat, Inc., Jon Magrini <jmagrini@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class MegaCLI(Plugin, RedHatPlugin):

    short_desc = 'LSI MegaRAID devices'

    plugin_name = 'megacli'
    profiles = ('system', 'storage', 'hardware')
    files = ('/opt/MegaRAID/MegaCli/MegaCli64',)

    def setup(self):
        cmd = '/opt/MegaRAID/MegaCli/MegaCli64'
        subcmds = [
            'LDPDInfo',
            '-AdpAllInfo',
            '-AdpBbuCmd -GetBbuStatus',
            '-ShowSummary'
        ]

        self.add_cmd_output([
            "%s %s -aALL" % (cmd, subcmd) for subcmd in subcmds
        ])

# vim: set et ts=4 sw=4 :
