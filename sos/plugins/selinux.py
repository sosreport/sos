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
    optionList = [("fixfiles", 'Print incorrect file context labels', 'slow', False),
                  ("list", 'List objects and their context', 'slow', False)]
    packages = ('libselinux', 'policycoreutils-python')

    def setup(self):
        self.addCopySpec("/etc/selinux")
        self.collectExtOutput("sestatus -b")
        self.collectExtOutput("semodule -l")
        self.collectExtOutput("selinuxdefcon root")
        self.collectExtOutput("selinuxconlist root")
        self.collectExtOutput("ausearch --input-logs -m avc,user_avc -ts today")
        self.collectExtOutput("semanage -o -")
        if self.getOption('fixfiles'):
            self.collectExtOutput("fixfiles check")
        if self.getOption('list'):
            self.collectExtOutput("semanage fcontext -l")
            self.collectExtOutput("semanage user -l")
            self.collectExtOutput("semanage login -l")
            self.collectExtOutput("semanage port -l")
            
