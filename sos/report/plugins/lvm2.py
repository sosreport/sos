# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, IndependentPlugin, SoSPredicate,
                                PluginOpt)


class Lvm2(Plugin, IndependentPlugin):

    short_desc = 'Logical Volume Manager 2'

    plugin_name = 'lvm2'
    profiles = ('storage',)

    option_list = [
        PluginOpt('lvmdump', default=False, desc='collect an lvmdump tarball'),
        PluginOpt('lvmdump-am', default=False,
                  desc=('attempt to collect lvmdump with advanced options and '
                        'raw metadata'))
    ]

    def do_lvmdump(self, metadata=False):
        """Collects an lvmdump in standard format with optional metadata
           archives for each physical volume present.
        """
        lvmdump_path = self.get_cmd_output_path(name="lvmdump", make=False)
        lvmdump_cmd = "lvmdump %s -d '%s'"
        lvmdump_opts = ""

        if metadata:
            lvmdump_opts = "-a -m"

        cmd = lvmdump_cmd % (lvmdump_opts, lvmdump_path)

        self.add_cmd_output(cmd, chroot=self.tmp_in_sysroot())

    def setup(self):
        # When running LVM2 comamnds:
        # - use nolocking if supported, else locking_type 0 (no locks)
        #   from lvm.conf: Turn locking off by setting to 0 (dangerous:
        #   risks metadata corruption if LVM2 commands get run
        #   concurrently).  This avoids the possibility of hanging lvm
        #   commands when another process or node holds a conflicting
        #   lock.
        # - use metadata_read_only 1 (forbid on-disk changes). Although
        #   all LVM2 commands we use should be read-only, any LVM2
        #   command may attempt to recover on-disk data in some cases.
        #   This option prevents such changes, allowing safe use of
        #   locking_type=0.
        # - use --foreign option in pvs, lvs, vgs and vgdisplay commands
        #   to support HA-LVM deployments
        nolock = {'cmd': 'vgdisplay -h', 'output': '--nolocking'}
        if bool(SoSPredicate(self, cmd_outputs=nolock)):
            lvm_opts = '--config="global{metadata_read_only=1}" --nolocking'
        else:
            lvm_opts = '--config="global{locking_type=0 metadata_read_only=1}"'
        lvm_opts_foreign = lvm_opts + ' --foreign'

        self.add_cmd_output(
            "vgdisplay -vv %s" % lvm_opts_foreign,
            root_symlink="vgdisplay"
        )

        pvs_cols = 'pv_mda_free,pv_mda_size,pv_mda_count,pv_mda_used_count'
        pvs_cols = pvs_cols + ',' + 'pe_start'
        vgs_cols = 'vg_mda_count,vg_mda_free,vg_mda_size,vg_mda_used_count'
        vgs_cols = vgs_cols + ',' + 'vg_tags,systemid'
        lvs_cols = ('lv_tags,devices,lv_kernel_read_ahead,lv_read_ahead,'
                    'stripes,stripesize')
        self.add_cmd_output([
            "vgscan -vvv %s" % lvm_opts,
            "pvscan -v %s" % lvm_opts,
            "pvs -a -v -o +%s %s" % (pvs_cols, lvm_opts_foreign),
            "vgs -v -o +%s %s" % (vgs_cols, lvm_opts_foreign),
            "lvs -a -o +%s %s" % (lvs_cols, lvm_opts_foreign)
        ])

        self.add_copy_spec("/etc/lvm")

        if self.get_option('lvmdump'):
            self.do_lvmdump()
        elif self.get_option('lvmdump-am'):
            self.do_lvmdump(metadata=True)

# vim: set et ts=4 sw=4 :
