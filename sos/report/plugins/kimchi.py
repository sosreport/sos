# Copyright IBM, Corp. 2014, Christy Perez <christy@linux.vnet.ibm.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Kimchi(Plugin, IndependentPlugin):

    short_desc = 'kimchi-related information'

    plugin_name = 'kimchi'
    packages = ('kimchi',)

    def setup(self):
        self.add_copy_spec('/etc/kimchi/')
        if not self.get_option('all_logs'):
            self.add_copy_spec('/var/log/kimchi/*.log')
            self.add_copy_spec('/etc/kimchi/kimchi*')
            self.add_copy_spec('/etc/kimchi/distros.d/*.json')
        else:
            self.add_copy_spec('/var/log/kimchi/')

# vim: expandtab tabstop=4 shiftwidth=4
