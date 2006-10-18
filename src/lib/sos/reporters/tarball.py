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

import sys
import sos.plugintools
from sos.helpers import *

class tarball(sos.plugintools.PluginBase):
    """This plugin tars up the information gathered by sosreport
    """
    def postproc(self, dstroot):
        print "Please enter your first initial and last name (jsmith): ",
        name = sys.stdin.readline()[:-1]

        print "Please enter the case number that you are generating this",
        print "report for: ",
        ticketNumber = sys.stdin.readline()[:-1]

        dirName = name + "." + ticketNumber
        self.callExtProg("/bin/mkdir /tmp/%s" % dirName)
        self.callExtProg("/bin/mv %s/* /tmp/%s"
                       % (dstroot, dirName))
        self.callExtProg("/bin/rm -rf %s" % dstroot)
        self.callExtProg("/bin/tar --directory /tmp -jcf "
                       "/tmp/%s.tar.bz2 %s"
                       % (dirName, dirName))
	self.callExtProg("/bin/rm -rf /tmp/%s" % dirName)
	print "Your tarball is located at /tmp/%s.tar.bz2" % dirName
        return "/tmp/" + dirName

