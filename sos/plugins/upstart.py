## Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Upstart(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ Information on Upstart, the event-based init system.
    """

    plugin_name = 'upstart'
    packages = ('upstart',)

    option_list = [("logsize", "maximum size (MiB) of logs to collect",
                   "", 15)]

    def setup(self):
        self.add_cmd_outputs([
            'initctl --system list',
            'initctl --system version',
            'init --version',
            "ls -l /etc/init/"
        ])

        # Job Configuration Files
        self.add_copy_specs([
            '/etc/init.conf',
            '/etc/init/'
        ])

        # State file
        self.add_copy_spec('/var/log/upstart/upstart.state')

        # Log files
        self.add_copy_spec_limit('/var/log/upstart/*',
                                 sizelimit=self.get_option('logsize'))
        # Session Jobs (running Upstart as a Session Init)
        self.add_copy_spec('/usr/share/upstart/')


# vim: et ts=4 sw=4
