# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import time
import os.path
import os
import glob
import string
from sos.plugins import Plugin, RedHatPlugin


class Gluster(Plugin, RedHatPlugin):
    """GlusterFS storage"""

    plugin_name = 'gluster'
    profiles = ('storage', 'virt')

    statedump_dir = '/tmp/glusterfs-statedumps'
    packages = ["glusterfs", "glusterfs-core"]
    files = ["/etc/glusterd", "/var/lib/glusterd"]

    option_list = [("dump", "enable glusterdump support", "slow", False)]

    def get_volume_names(self, volume_file):
        """Return a dictionary for which key are volume names according to the
        output of gluster volume info stored in volume_file.
        """
        out = []
        fp = open(volume_file, 'r')
        for line in fp.readlines():
            if not line.startswith("Volume Name:"):
                continue
            volname = line[12:-1]
            out.append(volname)
        fp.close()
        return out

    def make_preparations(self, name_dir):
        try:
            os.mkdir(name_dir)
        except OSError:
            pass
        fp = open('/tmp/glusterdump.options', 'w')
        data = 'path=' + name_dir + '\n'
        fp.write(data)
        fp.write('all=yes')
        fp.close()

    def wait_for_statedump(self, name_dir):
        statedumps_present = 0
        statedump_entries = os.listdir(name_dir)
        for statedump_file in statedump_entries:
            statedumps_present = statedumps_present+1
            ret = -1
            while ret == -1:
                last_line = file(
                    name_dir + '/' + statedump_file, "r").readlines()[-1]
                ret = string.count(last_line, 'DUMP_END_TIME')

    def postproc(self):
        if not os.path.exists(self.statedump_dir):
            return
        try:
            for dirs in os.listdir(self.statedump_dir):
                os.remove(os.path.join(self.statedump_dir, dirs))
            os.rmdir(self.statedump_dir)
            os.unlink('/tmp/glusterdump.options')
        except OSError:
            pass

    def setup(self):
        self.add_forbidden_path("/var/lib/glusterd/geo-replication/secret.pem")

        self.add_cmd_output("gluster peer status")

        self.add_copy_spec([
            "/etc/redhat-storage-release",
            # collect unified file and object storage configuration
            "/etc/swift/",
            # glusterfs-server rpm scripts stash this on migration to 3.3.x
            "/etc/glusterd.rpmsave",
            # common to all versions
            "/etc/glusterfs",
            "/var/lib/glusterd/",
            # collect nfs-ganesha related configuration
            "/var/run/gluster/shared_storage/nfs-ganesha/"
        ] + glob.glob('/var/run/gluster/*tier-dht/*'))

        # collect logs - apply log_size for any individual file
        # all_logs takes precedence over logsize
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
        else:
            limit = 0

        if limit:
            for f in (glob.glob("/var/log/glusterfs/*log") +
                      glob.glob("/var/log/glusterfs/*/*log") +
                      glob.glob("/var/log/glusterfs/geo-replication/*/*log")):
                self.add_copy_spec(f, limit)
        else:
            self.add_copy_spec("/var/log/glusterfs")

        if self.get_option("dump"):
            self.make_preparations(self.statedump_dir)
            if self.check_ext_prog("killall -USR1 glusterfs glusterfsd"):
                # let all the processes catch the signal and create
                # statedump file entries.
                time.sleep(1)
                self.wait_for_statedump(self.statedump_dir)
                self.add_copy_spec('/tmp/glusterdump.options')
                self.add_copy_spec(self.statedump_dir)
            else:
                self.soslog.info("could not send SIGUSR1 to glusterfs \
                processes")

        volume_file = self.get_cmd_output_now("gluster volume info")
        if volume_file:
            for volname in self.get_volume_names(volume_file):
                self.add_cmd_output([
                    "gluster volume geo-replication %s status" % volname,
                    "gluster volume heal %s info" % volname,
                    "gluster volume heal %s info split-brain" % volname,
                    "gluster snapshot list %s" % volname,
                    "gluster volume quota %s list" % volname,
                    "gluster volume rebalance %s status" % volname,
                    "gluster snapshot info %s" % volname,
                    "gluster snapshot status %s" % volname
                ])

        self.add_cmd_output("gluster pool list")
        self.add_cmd_output("gluster volume status")

# vim: set et ts=4 sw=4 :
