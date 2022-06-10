# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class OSTree(Plugin, IndependentPlugin):

    short_desc = 'OSTree'

    plugin_name = 'ostree'
    profiles = ('system', 'sysmgmt', 'packagemanager')
    files = ('/ostree',)
    services = ('ostree-finalize-staged', 'ostree-boot-complete')

    def setup(self):
        self.add_copy_spec("/ostree/repo/config")
        self.add_cmd_output([
            "ostree admin status",
            "ostree admin config-diff",
            "ostree refs",
        ])
        if self.get_option("verify"):
            self.add_cmd_output("ostree fsck")

# vim: set et ts=4 sw=4 :
