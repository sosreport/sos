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

class devicemapper(sos.plugintools.PluginBase):
    """This plugin gathers device-mapper related information (dm, lvm, multipath)
    """
    def setup(self):
        self.collectExtOutput("/sbin/dmsetup info -c")
        self.collectExtOutput("/sbin/dmsetup table")
        self.collectExtOutput("/sbin/dmsetup status")

        self.collectExtOutput("/usr/sbin/vgscan -vvv")
        self.collectExtOutput("/usr/sbin/vgdisplay -vv")
        self.collectExtOutput("/usr/sbin/pvscan -v")
        self.collectExtOutput("/usr/sbin/lvs -a -o +devices")
        self.collectExtOutput("/usr/sbin/pvs -a -v")
        self.collectExtOutput("/usr/sbin/vgs -v")

        self.addCopySpec("/etc/lvm/lvm.conf")

        self.addCopySpec("/etc/multipath.conf")
        self.addCopySpec("/var/lib/multipath/bindings")
        self.collectExtOutput("/sbin/multipath -v4 -ll")

        return
