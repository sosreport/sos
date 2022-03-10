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
    """
    This plugin gathers information for VNC servers provided by the tigervnc
    package. This is explicitly for server-side collections, not clients.

    By default, this plugin will capture the contents of /etc/tigervnc, which
    may include usernames. If usernames are sensitive information for end
    users of sos, consider using the `--clean` option to obfuscate these
    names.
    """

    short_desc = 'TigerVNC server configuration'
    plugin_name = 'tigervnc'
    packages = ('tigervnc-server',)

    def setup(self):
        self.add_copy_spec('/etc/tigervnc/')

        # service names are 'vncserver@$port' where $port is :1,, :2, etc...
        # however they are not reported via list-unit-files, only list-units
        vncs = self.exec_cmd(
            'systemctl list-units --type=service --no-legend vncserver*'
        )
        if vncs['status'] == 0:
            for serv in vncs['output'].splitlines():
                vnc = serv.split()
                if not vnc:
                    continue
                self.add_service_status(vnc[0])
                self.add_journal(vnc[0])

        self.add_cmd_output('vncserver -list')

# vim: set et ts=4 sw=4 :
