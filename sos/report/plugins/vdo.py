# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Vdo(Plugin, RedHatPlugin):

    short_desc = 'Virtual Data Optimizer'

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
        vdos = self.collect_cmd_output('vdo list --all')
        for vdo in vdos['output'].splitlines():
            self.add_cmd_output("vdo status -n %s" % vdo)
        self.add_cmd_output('vdostats --human-readable')

# vim set et ts=4 sw=4 :
