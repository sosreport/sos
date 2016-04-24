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


class SELinux(Plugin, RedHatPlugin):
    """SELinux access control
    """

    plugin_name = 'selinux'
    profiles = ('system', 'security', 'openshift')

    option_list = [("fixfiles", 'Print incorrect file context labels',
                    'slow', False),
                   ("list", 'List objects and their context', 'slow', False)]
    packages = ('libselinux',)

    def setup(self):
        self.add_copy_spec("/etc/selinux")
        self.add_cmd_output([
            "sestatus -b",
            "semodule -l",
            "selinuxdefcon root",
            "selinuxconlist root",
            "selinuxexeccon /bin/passwd",
            "semanage -o -",
            "ps axuZww"
        ])
        if self.get_option('fixfiles'):
            self.add_cmd_output("restorecon -Rvn /", stderr=False)
        if self.get_option('list'):
            self.add_cmd_output([
                "semanage fcontext -l",
                "semanage user -l",
                "semanage login -l",
                "semanage port -l"
            ])


# vim: set et ts=4 sw=4 :
