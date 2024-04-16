# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Xfs(Plugin, IndependentPlugin):
    """This plugin collects information on mounted XFS filessystems on the
    local system.

    Users should expect `xfs_info` and `xfs_admin` collections by this plugin
    for each XFS filesystem that is locally mounted.
    """

    short_desc = 'XFS filesystem'

    plugin_name = 'xfs'
    profiles = ('storage',)
    files = ('/sys/fs/xfs', '/proc/fs/xfs')
    kernel_mods = ('xfs',)

    def setup(self):
        mounts = '/proc/mounts'
        ext_fs_regex = r"^(/dev/.+).+xfs\s+"
        for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
            for ext in dev:
                parts = ext.split(' ')
                self.add_cmd_output(f"xfs_info {parts[1]}",
                                    tags="xfs_info")
                self.add_cmd_output(f"xfs_admin -l -u {parts[0]}")

        self.add_copy_spec([
            '/proc/fs/xfs',
            '/sys/fs/xfs'
        ])

# vim: set et ts=4 sw=4 :
