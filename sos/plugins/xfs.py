# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from six.moves import zip


class Xfs(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """XFS filesystem
    """

    plugin_name = 'xfs'
    profiles = ('storage',)

    def setup(self):
        mounts = '/proc/mounts'
        ext_fs_regex = r"^(/dev/.+).+xfs\s+"
        for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
            for e in dev:
                parts = e.split(' ')
                self.add_cmd_output("xfs_info %s" % (parts[1]))
                self.add_cmd_output("xfs_admin -l -u %s" % (parts[1]))

        self.add_copy_spec('/proc/fs/xfs')

# vim: set et ts=4 sw=4 :
