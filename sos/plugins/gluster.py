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

import time
import os.path
import os
import string
from sos.plugins import Plugin, RedHatPlugin

class gluster(Plugin, RedHatPlugin):
    '''gluster related information'''

    statedump_dir = '/tmp/glusterfs-statedumps'
    packages = ["glusterfs", "glusterfs-core"]
    files = ["/etc/glusterd", "/var/lib/glusterd"]

    def default_enabled(self):
        return True

    def get_volume_names(self, volume_file):
        """Return a dictionary for which key are volume names according to the
        output of gluster volume info stored in volume_file.
        """
        out=[]
        fp = open(volume_file, 'r')
        for line in fp.readlines():
            if not line.startswith("Volume Name:"):
                continue
            volname = line[14:-1]
            out.append(volname)
        fp.close()
        return out

    def make_preparations(self, name_dir):
        try:
            os.mkdir(name_dir);
        except:
            pass
        fp = open ('/tmp/glusterdump.options', 'w');
        data = 'path=' + name_dir + '\n';
        fp.write(data);
        fp.write('all=yes');
        fp.close();

    def wait_for_statedump(self, name_dir):
        statedumps_present = 0;
        statedump_entries = os.listdir(name_dir);
        for statedump_file in statedump_entries:
            statedumps_present = statedumps_present+1;
            last_line = 'tmp';
            ret = -1;
            while  ret == -1:
                last_line = file(name_dir + '/' + statedump_file, "r").readlines()[-1];
                ret = string.count (last_line, 'DUMP_END_TIME');

    def postproc(self):
        if not os.path.exists(self.statedump_dir):
            return
        try:
            for dirs in os.listdir(self.statedump_dir):
                os.remove(os.path.join(self.statedump_dir,dirs));
            os.rmdir(self.statedump_dir);
            os.unlink('/tmp/glusterdump.options');
        except:
            pass

    def setup(self):
        self.add_cmd_output("/usr/sbin/gluster peer status")

        # check package version handling rename of glusterfs-core -> glusterfs
        pkg = self.policy().pkg_by_name("glusterfs-core");
        if not pkg:
            pkg = self.policy().pkg_by_name("glusterfs");
            # need to handle "no package" case for users who enable with -e/-o
            if not pkg:
                return

        gluster_major = int((pkg["version"])[:1])
        gluster_minor = int((pkg["version"])[2:3])
        if (gluster_major == 3) and (gluster_minor <= 2):
            self.add_copy_spec("/etc/glusterd/")
            self.add_forbidden_path("/etc/glusterd/geo-replication/secret.pem")
        else:
            self.add_copy_spec("/var/lib/glusterd/")
            self.add_forbidden_path("/var/lib/glusterd/geo-replication/secret.pem")

        # collect unified file and object storage configuration
        self.add_copy_spec("/etc/swift/")

        # glusterfs-server rpm scripts stash this on migration to 3.3.x
        self.add_copy_spec("/etc/glusterd.rpmsave")

        # common to all versions
        self.add_copy_spec("/etc/glusterfs")

        self.make_preparations(self.statedump_dir)
        #self.add_cmd_output("killall -USR1 glusterfs glusterfsd")
        os.system("killall -USR1 glusterfs glusterfsd");
        # let all the processes catch the signal and create statedump file
        # entries.
        time.sleep(1)
        self.wait_for_statedump(self.statedump_dir)
        self.add_copy_spec('/tmp/glusterdump.options')
        self.add_copy_spec(self.statedump_dir)

        self.add_cmd_output("gluster volume status")
        # collect this last as some of the other actions create log entries
        self.add_copy_spec("/var/log/glusterfs")

