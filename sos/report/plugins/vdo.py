# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Vdo(Plugin, RedHatPlugin):

    short_desc = 'Virtual Data Optimizer'

    plugin_name = 'vdo'
    profiles = ('storage',)
    packages = ('vdo',)
    files = (
        '/sys/kvdo',
        '/sys/uds',
        '/etc/vdoconf.yml',
        '/etc/vdoconf.xml'
    )

    def setup(self):
        self.add_copy_spec(self.files)
        vdos = self.collect_cmd_output('vdo list --all')
        for vdo in vdos['output'].splitlines():
            self.add_cmd_output(f"vdo status -n {vdo}")
        self.add_cmd_output([
            'vdostats --human-readable',
            'vdostats --verbose',
        ])
        vdo_cols1 = ('vdo_slab_size,vdo_header_size,vdo_minimum_io_size,'
                     'vdo_block_map_cache_size,vdo_block_map_era_length,'
                     'vdo_write_policy,vdo_max_discard')

        vdo_cols2 = ('vdo_ack_threads,vdo_bio_rotation,vdo_bio_threads,'
                     'vdo_cpu_threads,vdo_hash_zone_threads,'
                     'vdo_logical_threads,vdo_physical_threads')
        vdo_cols3 = ('vdo_compression,vdo_deduplication,'
                     'vdo_use_metadata_hints,vdo_use_sparse_index,'
                     'vdo_index_state,vdo_index_memory_size')
        self.add_cmd_output([f"lvs -a -o +{cols}"
                             for cols in [vdo_cols1, vdo_cols2]])
        lvm_vdos = self.collect_cmd_output(f"lvs -a -o +{vdo_cols3}")
        if lvm_vdos['status'] == 0:
            for vdo in lvm_vdos['output'].splitlines():
                # we can find the pool and pool data maps in the output
                # of lvs, in the column Volume type, marked as 'D'
                lv, vg, lv_attr = vdo.split()[:3]
                if lv_attr.startswith("D"):
                    vdo_path = f"{vg}-{lv.strip('[]')}"
                    self.add_cmd_output(
                        f"vdodumpconfig /dev/mapper/{vdo_path}"
                    )

# vim set et ts=4 sw=4 :
