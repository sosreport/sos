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
import os, re
import time, libxml2
import glob

class corosync(sos.plugintools.PluginBase):
    """ corosync information
    """

    def checkenabled(self):
        self.files = ['/usr/sbin/corosync']
        self.packages = ['corosync']
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        self.collectExtOutput("corosync-quorumtool -l")
        self.collectExtOutput("corosync-quorumtool -s")
        self.collectExtOutput("corosync-cpgtool")
        self.collectExtOutput("corosync-objctl -a")
        self.collectExtOutput("corosync-fplay")
        self.addCopySpec("/var/lib/corosync/fdata")
        self.collectExtOutput("/usr/sbin/corosync-objctl -w runtime.blackbox.dump_state=$(date +\%s)")
        self.collectExtOutput("/usr/sbin/corosync-objctl -w runtime.blackbox.dump_flight_data=$(date +\%s)")
        self.callExtProg("killall -USR2 corosync")
        self.addCopySpec("/var/log/cluster/corosync.log")
