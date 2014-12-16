# Copyright IBM, Corp. 2014, Christy Perez <christy@linux.vnet.ibm.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Kimchi(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """kimchi-related information
    """

    plugin_name = 'kimchi'
    packages = ('kimchi',)

    def setup(self):
        log_limit = self.get_option('log_size')
        if not self.get_option('all_logs'):
            self.add_copy_spec_limit('/var/log/kimchi/*.log',
                                     sizelimit=log_limit)
            self.add_copy_spec_limit('/etc/kimchi/kimchi*',
                                     sizelimit=log_limit)
            self.add_copy_spec_limit('/etc/kimchi/distros.d/*.json',
                                     sizelimit=log_limit)
        else:
            self.add_copy_spec('/var/log/kimchi/')
            self.add_copy_spec('/etc/kimchi/')

# vim: expandtab tabstop=4 shiftwidth=4
