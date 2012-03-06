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

import sos.plugintools

class selinux(sos.plugintools.PluginBase):
    """selinux related information
    """
    optionList = [("fixfiles", 'Print incorrect file context labels', 'slow', False)]
    def setup(self):
        # sestatus is always collected in checkenabled()
        self.addCopySpec("/etc/selinux")
        self.collectExtOutput("/usr/bin/selinuxconfig")
        if self.getOption('fixfiles'):
            self.collectExtOutput("/sbin/fixfiles check")
        self.addForbiddenPath("/etc/selinux/targeted")

        return

    def checkenabled(self):
        # is selinux enabled ?
        try:
            if self.collectOutputNow("/usr/sbin/sestatus", symlink = "sestatus").split(":")[1].strip() == "disabled":
                return False
        except:
            pass
        return True

    def analyze(self):
        # Check for SELinux denials and capture raw output from sealert
        if self.policy().runlevelDefault() in self.policy().runlevelByService("setroubleshoot"):
            # TODO: fixup regex for more precise matching
            sealert=doRegexFindAll(r"^.*setroubleshoot:.*(sealert\s-l\s.*)","/var/log/messages")
            if sealert:
                for i in sealert:
                    self.collectExtOutput("%s" % i)
                self.addAlert("There are numerous selinux errors present and "+
                              "possible fixes stated in the sealert output.")
