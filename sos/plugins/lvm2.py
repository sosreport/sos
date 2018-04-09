# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Lvm2(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """LVM2 volume manager
    """

    plugin_name = 'lvm2'
    profiles = ('storage',)

    option_list = [("lvmdump", 'collect an lvmdump tarball', 'fast', False),
                   ("lvmdump-am", 'attempt to collect an lvmdump with '
                    'advanced options and raw metadata collection', 'slow',
                    False)]

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
        # use locking_type 0 (no locks) when running LVM2 commands,
        # from lvm.conf:
        # Turn locking off by setting to 0 (dangerous: risks metadata
        # corruption if LVM2 commands get run concurrently).
        # None of the commands issued by sos ever modify metadata and this
        # avoids the possibility of hanging lvm commands when another process
        # or node holds a conflicting lock.
        lvm_opts = '--config="global{locking_type=0}"'

        self.add_cmd_output(
            "vgdisplay -vv %s" % lvm_opts,
            root_symlink="vgdisplay"
        )

        pvs_cols = 'pv_mda_free,pv_mda_size,pv_mda_count,pv_mda_used_count'
        pvs_cols = pvs_cols + ',' + 'pe_start'
        vgs_cols = 'vg_mda_count,vg_mda_free,vg_mda_size,vg_mda_used_count'
        vgs_cols = vgs_cols + ',' + 'vg_tags'
        lvs_cols = 'lv_tags,devices'
        self.add_cmd_output([
            "vgscan -vvv %s" % lvm_opts,
            "pvscan -v %s" % lvm_opts,
            "pvs -a -v -o +%s %s" % (pvs_cols, lvm_opts),
            "vgs -v -o +%s %s" % (vgs_cols, lvm_opts),
            "lvs -a -o +%s %s" % (lvs_cols, lvm_opts)
        ])

        self.add_copy_spec("/etc/lvm")

        if self.get_option('lvmdump'):
            self.do_lvmdump()
        elif self.get_option('lvmdump-am'):
            self.do_lvmdump(metadata=True)

# vim: set et ts=4 sw=4 :
