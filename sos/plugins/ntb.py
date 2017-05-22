# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin


class Ntb(Plugin, RedHatPlugin):
    """Linux PCI-Express Non-Transparent Bridge
    """

    plugin_name = 'ntb'
    profiles = ('hardware', )

    def setup(self):
        # NTB is hardwired at PCI Bus 0, device 3, function 0 on Intel
        # processors (see page 8 in
        # http://download.intel.com/design/intarch/papers/323328.pdf).
        self.add_copy_spec([
            '/sys/kernel/debug/ntb_hw_intel/0000:*/info',
            '/sys/kernel/debug/ntb_transport/0000:*/qp*/stats'
        ])


# vim: set et ts=4 sw=4 :
