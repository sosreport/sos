# Copyright (C) 2017 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin


class Runc(Plugin):

    """runC container runtime"""

    plugin_name = 'runc'

    def setup(self):

        self.add_cmd_output('runc list')

        cons = self.get_command_output('runc list -q')
        conlist = [c for c in cons['output'].splitlines()]
        for con in conlist:
            self.add_cmd_output('runc ps %s' % con)
            self.add_cmd_output('runc state %s' % con)
            self.add_cmd_output('runc events --stats %s' % con)


class RedHatRunc(Runc, RedHatPlugin):

    packages = ('runc', )

    def setup(self):
        super(RedHatRunc, self).setup()
