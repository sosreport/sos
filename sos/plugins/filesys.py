# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Filesys(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Local file systems
    """

    plugin_name = 'filesys'
    profiles = ('storage',)

    option_list = [
        ("lsof", 'gathers information on all open files', 'slow', False),
        ("dumpe2fs", 'dump filesystem information', 'slow', False),
        ("frag", 'filesystem fragmentation status', 'slow', False)
    ]

    def setup(self):
        self.add_copy_spec([
            "/proc/fs/",
            "/proc/mounts"
            "/proc/filesystems",
            "/proc/self/mounts",
            "/proc/self/mountinfo",
            "/proc/self/mountstats",
            "/proc/[0-9]*/mountinfo",
            "/etc/fstab"
        ])
        self.add_cmd_output("mount -l", root_symlink="mount")
        self.add_cmd_output("df -al -x autofs", root_symlink="df")
        self.add_cmd_output([
            "df -ali -x autofs",
            "findmnt",
            "lslocks"
        ])

        if self.get_option('lsof'):
            self.add_cmd_output("lsof -b +M -n -l -P", root_symlink="lsof")

        dumpe2fs_opts = '-h'
        if self.get_option('dumpe2fs'):
            dumpe2fs_opts = ''
        mounts = '/proc/mounts'
        ext_fs_regex = r"^(/dev/.+).+ext[234]\s+"
        for dev in self.do_regex_find_all(ext_fs_regex, mounts):
                self.add_cmd_output("dumpe2fs %s %s" % (dumpe2fs_opts, dev))

                if self.get_option('frag'):
                    self.add_cmd_output("e2freefrag %s" % (dev))

    def postproc(self):
        self.do_file_sub(
            "/etc/fstab",
            r"(password=)[^\s]*",
            r"\1********"
        )

        # remove expected errors from lsof due to command formatting, but still
        # keep stderr so other errors are reported
        regex = (r"(lsof: (avoiding (.*?)|WARNING: can't stat\(\) (.*?))|"
                 "Output information may be incomplete.)\n")

        self.do_cmd_output_sub("lsof", regex, '')

# vim: set et ts=4 sw=4 :
