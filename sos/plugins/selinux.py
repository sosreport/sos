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

class selinux(Plugin, RedHatPlugin):
    """selinux related information
    """
    option_list = [("fixfiles", 'Print incorrect file context labels', 'slow', False)]
    def setup(self):
        # sestatus is always collected in check_enabled()
        self.add_copy_spec("/etc/selinux")
        self.add_cmd_output("/usr/bin/selinuxconfig")
        if self.get_option('fixfiles'):
            self.add_cmd_output("/sbin/fixfiles check")
        self.add_forbidden_path("/etc/selinux/targeted")

        if not self.policy().pkg_by_name('setroubleshoot'):
            return

        # Check for SELinux denials and capture raw output from sealert
        if self.policy().default_runlevel() in self.policy().runlevel_by_service("setroubleshoot"):
            # TODO: fixup regex for more precise matching
            sealert=do_regex_find_all(r"^.*setroubleshoot:.*(sealert\s-l\s.*)","/var/log/messages")
            if sealert:
                for i in sealert:
                    self.add_cmd_output("%s" % i)
                self.add_alert("There are numerous selinux errors present and "+
                              "possible fixes stated in the sealert output.")
    def check_enabled(self):
        try:
            if self.get_cmd_output_now("/usr/sbin/sestatus", root_symlink = "sestatus").split(":")[1].strip() == "disabled":
                return False
        except:
            pass
        return True
