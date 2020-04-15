# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin


class CephAnsible(Plugin, RedHatPlugin, DebianPlugin):

    short_desc = 'CEPH distributed storage - Ansible installer'

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
