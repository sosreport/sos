# Copyright (C) 2007 Shijoe George <spanjikk@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class TftpServer(Plugin, IndependentPlugin):

    short_desc = 'TFTP Server information'
    plugin_name = 'tftpserver'
    profiles = ('sysmgmt', 'network')

    files = ('/etc/xinetd.d/tftp',)
    packages = ('tftp-server',)

    def setup(self):
        self.add_cmd_output("ls -lanR /tftpboot")
        self.add_cmd_output('ls -lanR /srv/tftp')


# vim: set et ts=4 sw=4 :
