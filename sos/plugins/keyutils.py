# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Keyutils(Plugin, RedHatPlugin):
    """Kernel key ring
    """

    plugin_name = 'keyutils'
    profiles = ('system', 'kernel', 'security', 'storage')

    packages = ('keyutils',)

    def setup(self):
        self.add_copy_spec([
            "/etc/request-key.conf",
            "/etc/request-key.d",
            "/proc/key-users"
        ])
        self.add_cmd_output("keyctl show")

# vim: set et ts=4 sw=4 :
