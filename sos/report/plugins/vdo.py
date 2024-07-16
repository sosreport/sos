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
        vdo_cols = 'vdo_deduplication,vdo_index_state'
        lvs_opts = '-a -o +'
        lvm_vdos = self.collect_cmd_output(f"lvs {lvs_opts}{vdo_cols}")
        for vdo in lvm_vdos['output'].splitlines():
            # we can find the pool and pool data maps in the output
            # of lvs, in the column Volume type, marked as either 'd' or 'D'
            if vdo.split()[2].startswith("D"):
                vdo_path = f"{vdo.split()[1]}-{vdo.split()[0].strip('[]')}"
                self.add_cmd_output(f"vdodumpconfig /dev/mapper/{vdo_path}")

# vim set et ts=4 sw=4 :
