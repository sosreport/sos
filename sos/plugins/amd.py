## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

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

class Amd(Plugin, RedHatPlugin):
    """Amd automounter information
    """
    files = ('/etc/rc.d/init.d/amd',)
    packages = ('am-utils',)

    def setup(self):
        self.add_copy_specs("/etc/amd.*")
        self.add_cmd_output("egrep -e 'automount|pid.*nfs' /proc/mounts")
        self.add_cmd_output("mount | egrep -e 'automount|pid.*nfs'")
