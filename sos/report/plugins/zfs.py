# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import Plugin, IndependentPlugin


class Zfs(Plugin, IndependentPlugin):

    short_desc = 'ZFS filesystem'

    plugin_name = 'zfs'
    profiles = ('storage',)

    packages = ('zfsutils-linux', 'zfs',)

    def setup(self):
        self.add_cmd_output([
            "zfs get all",
            "zfs list -t all -o space",
            "zpool list",
            "zpool events -v",
            "zpool status -vx"
        ])

        zpools = self.collect_cmd_output("zpool list -H -o name")
        if zpools['status'] == 0:
            zpools_list = zpools['output'].splitlines()
            for zpool in zpools_list:
                self.add_cmd_output("zpool get all %s" % zpool)

# vim: set et ts=4 sw=4 :
