# Copyright (C) 2014 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
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


class kubernetes(Plugin, RedHatPlugin):

    """Kubernetes plugin
    """

    def setup(self):
        self.add_copy_spec("/etc/kubernetes")
        self.add_copy_spec("/etc/etcd")
        self.add_copy_spec("/var/run/flannel")

        # Kubernetes master info
        self.add_cmd_output("kubectl version")
        self.add_cmd_output("kubectl get -o json pods")
        self.add_cmd_output("kubectl get -o json minions")
        self.add_cmd_output("kubectl get -o json replicationController")
        self.add_cmd_output("kubectl get -o json events")
        self.add_cmd_output("journalctl -r -u kubelet")

        # etcd
        self.add_cmd_output("curl http://127.0.0.1:4001/version")
        self.add_cmd_output("curl http://127.0.0.1:4001/v2/members")
        self.add_cmd_output("curl http://127.0.0.1:4001/v2/stats/leader")
        self.add_cmd_output("curl http://127.0.0.1:4001/v2/stats/self")
        self.add_cmd_output("curl http://127.0.0.1:4001/v2/stats/store")


# vim: et ts=5 sw=4
