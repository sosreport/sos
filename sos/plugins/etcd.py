# Copyright (C) 2015 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2015 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
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


class etcd(Plugin, RedHatPlugin):

    """etcd plugin
    """

    def setup(self):
        self.add_copy_spec("/etc/etcd")

        self.add_cmd_output("curl http://localhost:4001/version")
        self.add_cmd_output("curl http://localhost:4001/v2/members")
        self.add_cmd_output("curl http://localhost:4001/v2/stats/leader")
        self.add_cmd_output("curl http://localhost:4001/v2/stats/self")
        self.add_cmd_output("curl http://localhost:4001/v2/stats/store")
        self.add_cmd_output("ls -lR /var/lib/etcd/")


# vim: et ts=5 sw=4
