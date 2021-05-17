# Copyright (C) 2021 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class TigerVNC(Plugin, RedHatPlugin):

    short_desc = 'TigerVNC server configuration'
    plugin_name = 'tigervnc'
    packages = ('tigervnc-server',)

    def setup(self):
        self.add_copy_spec([
            '/etc/tigervnc/vncserver-config-defaults',
            '/etc/tigervnc/vncserver-config-mandatory',
            '/etc/tigervnc/vncserver.users'
        ])

        self.add_cmd_output('vncserver -list')

# vim: set et ts=4 sw=4 :
