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

import os.path
import sos.plugintools

class gluster(sos.plugintools.PluginBase):
    '''gluster related information'''

    def defaultenabled(self):
        return False

    def get_volume_names(self, volume_file):
        """Return a dictionary for which key are volume names according to the
        output of gluster volume info stored in volume_file.
        """
        out=[]
        fp = open(volume_file, 'r')
        for line in fp.readlines():
            if not line.startswith("Volume Name:"):
                continue
            volname = line[12:]
            out.append(volname)
        fp.close()
        return out

    def checkenabled(self):
        packages = ["glusterfs", "glusterfs-core"]
        return os.path.exists("/etc/glusterd")               \
            or os.path.exists("/var/lib/glusterd")           \
            or sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        self.collectExtOutput("/usr/sbin/gluster peer status")

        pkg = self.policy().pkgByName("glusterfs-core");

        # need to handle "no package" case for users who force-enable with -e/-o
        if not pkg:
            return

        gluster_major = int((pkg["version"])[:1])
        gluster_minor = int((pkg["version"])[2:3])
        if (gluster_major == 3) and (gluster_minor <= 2):
            self.addCopySpec("/etc/glusterd/")
            self.addForbiddenPath("/etc/glusterd/geo-replication/secret.pem")
        else:
            self.addCopySpec("/var/lib/glusterd/")

        self.addCopySpec("/etc/glusterfs")
            
        volume_file = self.collectOutputNow("/usr/sbin/gluster volume info",
                        "gluster_volume_info")
        if volume_file:
            for volname in self.get_volume_names(volume_file):
                self.collectExtOutput("gluster volume statedump %s" % volname)
                self.collectExtOutput("gluster volume status %s detail" % volname)
                self.collectExtOutput("gluster volume status %s clients" % volname)
                self.collectExtOutput("gluster volume status %s mem" % volname)
                self.collectExtOutput("gluster volume status %s callpool" % volname)
                self.collectExtOutput("gluster volume status %s inode" % volname)
                self.collectExtOutput("gluster volume status %s fd" % volname)

        self.collectExtOutput("gluster volume status")
        # collect this last as some of the other actions create log entries
        self.addCopySpec("/var/log/glusterfs")
