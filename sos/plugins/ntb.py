# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
