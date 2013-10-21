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

    def setup(self):
        self.add_cmd_output('initctl --system list')
        self.add_cmd_output('initctl --system version')
        self.add_cmd_output('init --version')
        self.add_cmd_output("ls -l /etc/init/")

        # Job Configuration Files
        self.add_copy_spec('/etc/init.conf')
        self.add_copy_spec('/etc/init/')

        # State file
        self.add_copy_spec('/var/log/upstart/upstart.state')

        # Session Jobs (running Upstart as a Session Init)
        self.add_copy_spec('/usr/share/upstart/')

