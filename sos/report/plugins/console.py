# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from glob import glob
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Console(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Console and keyboard information'

    plugin_name = 'console'
    profiles = ('system',)
    packages = ('kbd',)

    def setup(self):
        self.add_copy_spec("/proc/consoles")

        self.add_cmd_output("fgconsole")
        self.add_cmd_output([
            "kbdinfo -C %s gkbled" % tty for tty in glob("/dev/tty[0-8]")
        ])

# vim: set et ts=4 sw=4 :
