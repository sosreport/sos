# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Ansible(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Ansible configuration management'

    plugin_name = 'ansible'
    profiles = ('system',)

    packages = (
        'ansible',
        'ansible1.9'
    )

    def setup(self):
        self.add_copy_spec("/etc/ansible/")

        self.add_cmd_output([
            "ansible all -m ping -vvvv",
            "ansible --version"
        ])

        # let rhui plugin collects the RHUI specific files
        self.add_forbidden_path("/etc/ansible/facts.d/rhui_*.fact")

# vim: set et ts=4 sw=4 :
