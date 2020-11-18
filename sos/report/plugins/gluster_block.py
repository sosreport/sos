# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import glob
from sos.report.plugins import Plugin, RedHatPlugin


class GlusterBlock(Plugin, RedHatPlugin):

    short_desc = 'Gluster Block'

    plugin_name = 'gluster_block'
    profiles = ('storage',)
    packages = ("gluster-block",)
    files = ("/usr/sbin/gluster-block",)

    def setup(self):

        # collect logs - apply log_size for any individual file
        # all_logs takes precedence over logsize
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
        else:
            limit = 0

        if limit:
            for f in glob.glob("/var/log/gluster-block/*.log"):
                self.add_copy_spec(f, limit)
        else:
            self.add_copy_spec("/var/log/gluster-block")
