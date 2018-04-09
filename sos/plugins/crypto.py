# Copyright (C) 2017 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Crypto(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ System crypto services information
    """

    plugin_name = 'crypto'
    profiles = ('system', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/proc/crypto",
            "/proc/sys/crypto/fips_enabled"
        ])

# vim: et ts=4 sw=4
