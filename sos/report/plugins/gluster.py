# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import os
import time
from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class Gluster(Plugin, RedHatPlugin):

    short_desc = 'GlusterFS storage'

    plugin_name = 'gluster'
    profiles = ('storage', 'virt')

    statedump_dir = '/run/gluster'
    packages = ("glusterfs", "glusterfs-core")
    files = ("/etc/glusterd", "/var/lib/glusterd")

    option_list = [
        PluginOpt("dump", default=False, desc="enable glusterdump support")
    ]

    def wait_for_statedump(self, name_dir):
        """ Wait until state dump is done """
        statedumps_present = 0
        statedump_entries = [
                f for f in self.listdir(name_dir) if self.path_isfile(f)
        ]
        for statedump_file in statedump_entries:
            statedumps_present = statedumps_present+1
            _spath = self.path_join(name_dir, statedump_file)
            ret = -1
            while ret == -1:
                with open(_spath, 'r', encoding='UTF-8') as sfile:
                    last_line = sfile.readlines()[-1]
                    ret = last_line.count('DUMP_END_TIME')

    def postproc(self):
        if self.get_option("dump"):
            if not self.path_exists(self.statedump_dir):
                return
            try:
                remove_files = glob.glob(self.statedump_dir + '/*.dump.[0-9]*')
                remove_files.extend(glob.glob(self.statedump_dir +
                                    '/glusterd_state_[0-9]*_[0-9]*'))
                for name in remove_files:
                    os.remove(name)
            except OSError as err:
                self._log_error(f"Could not remove statedump files: {err}")

    def setup(self):
        self.add_forbidden_path("/var/lib/glusterd/geo-replication/secret.pem")
        self.add_forbidden_path(
            "/var/lib/glusterd/glusterfind/glusterfind_*_secret.pem"
        )

        self.add_cmd_output("gluster peer status", tags="gluster_peer_status")
        self.add_cmd_output("gluster pool list")
        self.add_cmd_output("gluster volume status",
                            tags="gluster_v_status")

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
            if self.path_exists(self.statedump_dir):
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
                self.soslog.warning("Unable to generate statedumps, no such "
                                    "directory: %s", self.statedump_dir)
            state = self.exec_cmd("gluster get-state")
            if state['status'] == 0:
                state_file = state['output'].split()[-1]
                self.add_copy_spec(state_file)

        volume_cmd = self.collect_cmd_output("gluster volume info",
                                             tags="gluster_v_info")
        if volume_cmd['status'] == 0:
            for line in volume_cmd['output'].splitlines():
                if not line.startswith("Volume Name:"):
                    continue
                volname = line[12:]
                self.add_cmd_output([
                    f"gluster volume get {volname} all",
                    f"gluster volume geo-replication {volname} status",
                    f"gluster volume heal {volname} info",
                    f"gluster volume heal {volname} info split-brain",
                    f"gluster volume status {volname} clients",
                    f"gluster snapshot list {volname}",
                    f"gluster volume quota {volname} list",
                    f"gluster volume rebalance {volname} status",
                    f"gluster snapshot info {volname}",
                    f"gluster snapshot status {volname}",
                ])

# vim: set et ts=4 sw=4 :
