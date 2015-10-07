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

    option_list = [("podslog", "capture logs for pods", 'slow', False)]

    def setup(self):
        self.add_copy_spec("/etc/kubernetes")
        self.add_copy_spec("/var/run/flannel")

        # Kubernetes master info
        self.add_cmd_output("kubectl version")
        self.add_cmd_output("kubectl get -o json pods")
        self.add_cmd_output("kubectl get -o json nodes")
        self.add_cmd_output("kubectl get -o json services")
        self.add_cmd_output("kubectl get -o json replicationController")
        self.add_cmd_output("kubectl get -o json events")
        self.add_cmd_output("journalctl -u kubelet")
        self.add_cmd_output("journalctl -u kube-apiserver")
        self.add_cmd_output("journalctl -u kube-controller-manager")
        self.add_cmd_output("journalctl -u kube-scheduler")
        self.add_cmd_output("journalctl -u kube-proxy")

        if self.get_option('podslog'):
            result = self.get_command_output("kubectl get pods")
            if result['status'] == 0:
                for line in result['output'].splitlines()[1:]:
                    pod_name = line.split(" ")[0]
                    self.add_cmd_output([
                        "{0} log {1}".format("kubectl", pod_name)
                    ])


# vim: et ts=5 sw=4
