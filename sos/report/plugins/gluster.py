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
from sos.report.plugins import Plugin, RedHatPlugin


class Gluster(Plugin, RedHatPlugin):

    short_desc = 'GlusterFS storage'

    plugin_name = 'gluster'
    profiles = ('storage', 'virt')

    statedump_dir = '/run/gluster'
    packages = ("glusterfs", "glusterfs-core")
    files = ("/etc/glusterd", "/var/lib/glusterd")

    option_list = [("dump", "enable glusterdump support", "slow", False)]

    def wait_for_statedump(self, name_dir):
        statedumps_present = 0
        statedump_entries = [
                f for f in os.listdir(name_dir) if os.path.isfile(f)
        ]
        for statedump_file in statedump_entries:
            statedumps_present = statedumps_present+1
            ret = -1
            while ret == -1:
                with open(name_dir + '/' + statedump_file, 'r') as sfile:
                    last_line = sfile.readlines()[-1]
                    ret = string.count(last_line, 'DUMP_END_TIME')

    def postproc(self):
        if self.get_option("dump"):
            if not os.path.exists(self.statedump_dir):
                return
            try:
                remove_files = glob.glob(self.statedump_dir + '/*.dump.[0-9]*')
                remove_files.extend(glob.glob(self.statedump_dir +
                                    '/glusterd_state_[0-9]*_[0-9]*'))
                for name in remove_files:
                    os.remove(name)
            except OSError:
                pass

    def setup(self):
        self.add_forbidden_path("/var/lib/glusterd/geo-replication/secret.pem")
        self.add_forbidden_path(
            "/var/lib/glusterd/glusterfind/glusterfind_*_secret.pem"
        )

        self.add_cmd_output([
            "gluster peer status",
            "gluster pool list",
            "gluster volume status"
        ])

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
            "/run/gluster/shared_storage/nfs-ganesha/",
            # collect public ssh keys (a_s_c skips implicit hidden files)
            "/var/lib/glusterd/glusterfind/.keys/",
        ] + glob.glob('/run/gluster/*tier-dht/*'))

        if not self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/glusterfs/*log",
                "/var/log/glusterfs/*/*log",
                "/var/log/glusterfs/geo-replication/*/*log"
            ])
        else:
            self.add_copy_spec("/var/log/glusterfs")

        if self.get_option("dump"):
            if os.path.exists(self.statedump_dir):
                statedump_cmd = "killall -USR1 glusterfs glusterfsd glusterd"
                if self.exec_cmd(statedump_cmd)['status'] == 0:
                    # let all the processes catch the signal and create
                    # statedump file entries.
                    time.sleep(1)
                    self.wait_for_statedump(self.statedump_dir)
                    self.add_copy_spec(self.statedump_dir)
                else:
                    self.soslog.info("could not send SIGUSR1 to glusterfs/"
                                     "glusterd processes")
            else:
                self.soslog.warn("Unable to generate statedumps, no such "
                                 "directory: %s" % self.statedump_dir)
            state = self.exec_cmd("gluster get-state")
            if state['status'] == 0:
                state_file = state['output'].split()[-1]
                self.add_copy_spec(state_file)

        volume_cmd = self.collect_cmd_output("gluster volume info")
        if volume_cmd['status'] == 0:
            for line in volume_cmd['output'].splitlines():
                if not line.startswith("Volume Name:"):
                    continue
                volname = line[12:]
                self.add_cmd_output([
                    "gluster volume get %s all" % volname,
                    "gluster volume geo-replication %s status" % volname,
                    "gluster volume heal %s info" % volname,
                    "gluster volume heal %s info split-brain" % volname,
                    "gluster volume status %s clients" % volname,
                    "gluster snapshot list %s" % volname,
                    "gluster volume quota %s list" % volname,
                    "gluster volume rebalance %s status" % volname,
                    "gluster snapshot info %s" % volname,
                    "gluster snapshot status %s" % volname
                ])

# vim: set et ts=4 sw=4 :
