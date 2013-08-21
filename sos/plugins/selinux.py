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

from sos.plugins import Plugin, RedHatPlugin
from os.path import join

class SELinux(Plugin, RedHatPlugin):
    """selinux related information
    """

    plugin_name = 'selinux'

    option_list = [("fixfiles", 'Print incorrect file context labels', 'slow', False),
                   ("list", 'List objects and their context', 'slow', False)]
    packages = ('libselinux',)

    def setup(self):
        # sestatus is always collected in check_enabled()
        self.add_copy_spec("/etc/selinux")
        self.add_cmd_output("sestatus -b")
        self.add_cmd_output("semodule -l")
        self.add_cmd_output("selinuxdefcon root")
        self.add_cmd_output("selinuxconlist root")
        self.add_cmd_output("selinuxexeccon /bin/passwd")
        self.add_cmd_output("ausearch -m avc,user_avc -ts today")
        semanage_custom_dest = join(self.get_cmd_dir(),
                                    "selinux.custom")
        self.add_cmd_output("semanage -o %s" % semanage_custom_dest)
        if self.get_option('fixfiles'):
            self.add_cmd_output("fixfiles -v check")
        if self.get_option('list'):
            self.add_cmd_output("semanage fcontext -l")
            self.add_cmd_output("semanage user -l")
            self.add_cmd_output("semanage login -l")
            self.add_cmd_output("semanage port -l")

