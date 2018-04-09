# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Libraries(Plugin, RedHatPlugin, UbuntuPlugin):
    """Dynamic shared libraries
    """

    plugin_name = 'libraries'
    profiles = ('system',)

    option_list = [
        ('ldconfigv', 'collect verbose ldconfig output', "slow", False)
    ]

    def setup(self):
        self.add_copy_spec(["/etc/ld.so.conf", "/etc/ld.so.conf.d"])
        if self.get_option("ldconfigv"):
            self.add_cmd_output("ldconfig -v -N -X")
        self.add_cmd_output("ldconfig -p -N -X")

# vim: set et ts=4 sw=4 :
