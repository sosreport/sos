# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class CephAnsible(Plugin, RedHatPlugin, DebianPlugin):
    """CEPH distributed storage - Ansible installer
    """

    plugin_name = 'ceph_ansible'
    profiles = ('storage',)

    packages = ('ceph-ansible',)

    def setup(self):
        self.add_copy_spec([
            "/usr/share/ceph-ansible/group_vars/",
            "/usr/share/ceph-ansible/site*.yml",
            "/usr/share/ceph-ansible/ansible.cfg"
        ])

        self.add_forbidden_path("/usr/share/ceph-ansible/group_vars/*.sample")

# vim: set et ts=4 sw=4 :
