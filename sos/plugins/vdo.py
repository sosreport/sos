# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Vdo(Plugin, RedHatPlugin):
    """Virtual Data Optimizer
    """

    plugin_name = 'vdo'
    profiles = ('storage',)
    packages = ('vdo',)
    files = (
        '/sys/kvdo',
        '/sys/uds',
        '/etc/vdoconf.yml',
        '/etc/vdoconf.xml'
    )

    def setup(self):
        self.add_copy_spec(self.files)
        self.add_cmd_output("vdo status")

# vim set et ts=4 sw=4 :
