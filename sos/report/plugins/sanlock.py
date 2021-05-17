# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class SANLock(Plugin):

    short_desc = 'SANlock daemon'
    plugin_name = "sanlock"
    profiles = ('cluster', 'virt')
    packages = ("sanlock",)

    def setup(self):
        self.add_copy_spec("/var/log/sanlock.log*")
        self.add_cmd_output([
            "sanlock client status -D",
            "sanlock client host_status -D",
            "sanlock client log_dump"
        ])
        return


class RedHatSANLock(SANLock, RedHatPlugin):

    files = ("/etc/sysconfig/sanlock",)

    def setup(self):
        super(RedHatSANLock, self).setup()
        self.add_copy_spec("/etc/sysconfig/sanlock")

# vim: set et ts=4 sw=4 :
