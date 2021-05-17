# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
from re import match
import glob


class Peripety(Plugin, RedHatPlugin):

    short_desc = 'Peripety Storage Event Monitor'
    plugin_name = 'peripety'
    packages = ('peripety',)
    services = ('peripetyd',)

    def setup(self):
        self.add_copy_spec('/etc/peripetyd.conf')

        forbid_reg = [
            'vd.*',
            'sr.*',
            'loop.*',
            'ram.*'
        ]

        disks = filter(lambda x: not any(match(reg, x) for reg in forbid_reg),
                       [d.split('/')[-1] for d in glob.glob('/sys/block/*')])

        for disk in disks:
            self.add_cmd_output([
                "prpt info %s" % disk,
                "prpt query --blk %s" % disk
            ])
        self.add_journal('peripetyd')

# vim: set et ts=4 sw=4 :
