# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class MrgMessg(Plugin, RedHatPlugin):
    """MRG Messaging subsystem
    """

    plugin_name = 'mrgmessg'
    profiles = ('mrg',)

    def setup(self):
        self.add_copy_spec([
            "/etc/qpidd.conf",
            "/etc/sasl2/qpidd.conf",
            "/var/rhm"
        ])

# vim: set et ts=4 sw=4 :
