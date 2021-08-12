# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Gfs2(Plugin, IndependentPlugin):

    short_desc = 'GFS2 (Global Filesystem 2)'

    plugin_name = "gfs2"
    profiles = ("cluster", )
    packages = ("gfs2-utils",)

    option_list = [
        PluginOpt('lockdump', default=False,
                  desc='collect lock dumps for all GFS2 filesystems')
    ]

    def setup(self):
        self.add_copy_spec([
            "/sys/fs/gfs2/*/withdraw"
        ])
        self.add_cmd_output([
            "gfs_control ls -n",
            "gfs_control dump"
        ])

        if self.get_option("gfs2lockdump"):
            self.add_copy_spec("/sys/kernel/debug/gfs2/*")

# vim: et ts=4 sw=4
