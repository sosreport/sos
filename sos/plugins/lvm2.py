# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Lvm2(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """lvm2 related information
    """

    plugin_name = 'lvm2'

    option_list = [("lvmdump", 'collect an lvmdump tarball', 'fast', False),
                   ("lvmdump-am", 'attempt to collect an lvmdump with '
                    'advanced options and raw metadata collection', 'slow',
                    False)]

    def do_lvmdump(self, metadata=False):
        """Collects an lvmdump in standard format with optional metadata
           archives for each physical volume present.
        """
        lvmdump_cmd = "lvmdump %s -d '%s'"
        lvmdump_opts = ""
        if metadata:
            lvmdump_opts = "-a -m"
        cmd = lvmdump_cmd % (lvmdump_opts,
                             self.get_cmd_output_path(name="lvmdump"))
        self.add_cmd_output(cmd)

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
        self.add_cmd_outputs([
            "vgscan -vvv %s" % lvm_opts,
            "pvscan -v %s" % lvm_opts,
            "pvs -a -v %s" % lvm_opts,
            "vgs -v %s" % lvm_opts,
            "lvs -a -o +devices %s" % lvm_opts
        ])

        self.add_copy_spec("/etc/lvm")

        if self.get_option('lvmdump'):
            self.do_lvmdump()
        elif self.get_option('lvmdump-am'):
            self.do_lvmdump(metadata=True)

# vim: et ts=4 sw=4
