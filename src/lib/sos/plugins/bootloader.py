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

class bootloader(sos.plugintools.PluginBase):
    """Bootloader information
    """
    def setup(self):
        self.addCopySpec("/etc/lilo.conf")
        self.addCopySpec("/etc/milo.conf")
        self.addCopySpec("/etc/silo.conf")
        self.addCopySpec("/boot/efi/efi/redhat/elilo.conf")
        self.addCopySpec("/boot/grub/grub.conf")
        self.addCopySpec("/boot/grub/device.map")
        self.addCopySpec("/boot/yaboot.conf")
        
        self.collectExtOutput("/sbin/lilo -q")
        self.collectExtOutput("/bin/ls -laR /boot")
        return

