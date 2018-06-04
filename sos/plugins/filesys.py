# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Filesys(Plugin, DebianPlugin, UbuntuPlugin):
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


class RedHatFilesys(Filesys, RedHatPlugin):

    def setup(self):
        super(RedHatFilesys, self).setup()
        self.add_cmd_output("ls -ltradZ /tmp")

# vim: set et ts=4 sw=4 :
