# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Alternatives(Plugin, RedHatPlugin):
    """System alternatives
    """

    packages = ('chkconfig',)
    commands = ('alternatives',)

    def setup(self):
        self.add_cmd_output([
            'alternatives --list',
            'alternatives --version'
        ])

        alts = []
        ignore = [
            'cdrecord',
            'ld',
            'mkisofs',
            'whois',
            'xinputrc'
        ]

        res = self.get_command_output('alternatives --list')
        if res['status'] == 0:
            for line in res['output'].splitlines():
                alt = line.split()[0]
                if alt not in ignore:
                    alts.append(alt)
            disp_cmd = "alternatives --display %s"
            self.add_cmd_output([disp_cmd % alt for alt in alts])

# vim: set et ts=4 sw=4 :
