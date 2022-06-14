# Copyright (C) 2018 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Host(Plugin, IndependentPlugin):
    """This plugin primarily collects hostname related information, as well
    as a few collections that do not fit well in other plugins. For example,
    uptime information and SoS configuration data from /etc/sos.

    This plugin is not intended to be a catch-all "general" plugin however for
    these types of collections that do not have a specific component/package
    or pre-existing plugin.
    """

    short_desc = 'Host information'

    plugin_name = 'host'
    profiles = ('system',)

    def setup(self):

        self.add_forbidden_path('/etc/sos/cleaner')

        self.add_cmd_output('hostname', root_symlink='hostname')
        self.add_cmd_output('uptime', root_symlink='uptime')

        self.add_cmd_output('find / -maxdepth 2 -type l -ls',
                            root_symlink='root-symlinks')

        self.add_cmd_output([
            'hostname -f',
            'hostid',
            'hostnamectl status'
        ])

        self.add_copy_spec([
            '/etc/sos',
            '/etc/hostid',
        ])

        self.add_env_var([
            'REMOTEHOST',
            'TERM',
            'COLORTERM'
        ])
