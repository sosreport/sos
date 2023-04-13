# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import Plugin, IndependentPlugin


class Zfs(Plugin, IndependentPlugin):

    short_desc = 'ZFS filesystem'

    plugin_name = 'zfs'
    profiles = ('storage',)

    packages = ('zfsutils-linux', 'zfs',)

    def setup(self):
        self.add_cmd_output([
            "zfs get all",
            "zfs list -t all -o space",
            "zpool list",
            "zpool events -v",
            "zpool status -vx"
        ])

        self.add_copy_spec([
            "/proc/spl/kmem/slab",
            "/proc/spl/kstat/zfs/fm",
            "/proc/spl/kstat/zfs/zil",
            "/proc/spl/kstat/zfs/dbufs",
            "/proc/spl/kstat/zfs/dbgmsg",
            "/proc/spl/kstat/zfs/dmu_tx",
            "/proc/spl/kstat/zfs/abdstats",
            "/proc/spl/kstat/zfs/arcstats",
            "/proc/spl/kstat/zfs/dbufstats",
            "/proc/spl/kstat/zfs/dnodestats",
            "/proc/spl/kstat/zfs/xuio_stats",
            "/proc/spl/kstat/zfs/zfetchstats",
            "/proc/spl/kstat/zfs/import_progress",
            "/proc/spl/kstat/zfs/fletcher_4_bench",
            "/proc/spl/kstat/zfs/vdev_cache_stats",
            "/proc/spl/kstat/zfs/vdev_raidz_bench",
            "/proc/spl/kstat/zfs/vdev_mirror_stats",
            "/proc/spl/taskq",
            "/proc/spl/taskq-all",
        ])

        zpools = self.collect_cmd_output("zpool list -H -o name")
        if zpools['status'] == 0:
            zpools_list = zpools['output'].splitlines()
            for zpool in zpools_list:
                self.add_cmd_output("zpool get all %s" % zpool)

# vim: set et ts=4 sw=4 :
