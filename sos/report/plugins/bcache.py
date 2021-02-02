# Copyright (C) 2021, Canonical ltd
# Ponnuvel Palaniyappan <ponnuvel.palaniyappan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate


class Bcache(Plugin, IndependentPlugin):

    short_desc = 'Bcache statistics'

    plugin_name = 'bcache'
    profiles = ('storage', 'hardware')
    files = ('/sys/fs/bcache',)

    def setup(self):

        # Caution: reading /sys/fs/bcache/*/cache0/priority_stats is known
        # to degrade performance on old kernels. Needs care if that's ever
        # considered for inclusion here.
        # see: https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1840043
        self.add_forbidden_path([
            '/sys/fs/bcache/*/*/priority_stats',
        ])

        self.add_copy_spec([
            '/sys/block/bcache*/bcache/cache/internal/copy_gc_enabled',
            '/sys/block/bcache*/bcache/cache_mode',
            '/sys/block/bcache*/bcache/dirty_data',
            '/sys/block/bcache*/bcache/io_errors',
            '/sys/block/bcache*/bcache/sequential_cutoff',
            '/sys/block/bcache*/bcache/stats_hour/bypassed',
            '/sys/block/bcache*/bcache/stats_hour/cache_hit_ratio',
            '/sys/block/bcache*/bcache/stats_hour/cache_hits',
            '/sys/block/bcache*/bcache/stats_hour/cache_misses',
            '/sys/block/bcache*/bcache/writeback_percent',
            '/sys/fs/bcache/*/average_key_size',
            '/sys/fs/bcache/*/bdev*/*',
            '/sys/fs/bcache/*/bdev*/stat_*/*',
            '/sys/fs/bcache/*/block_size',
            '/sys/fs/bcache/*/bucket_size',
            '/sys/fs/bcache/*/cache_available_percent',
            '/sys/fs/bcache/*/congested_*_threshold_us',
            '/sys/fs/bcache/*/internal/*',
            '/sys/fs/bcache/*/stats_*/*',
            '/sys/fs/bcache/*/tree_depth',
        ], pred=SoSPredicate(self, kmods=['bcache']))

# vim: set et ts=4 sw=4 :
