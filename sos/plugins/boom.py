# Copyright (C) 2017 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Boom(Plugin, RedHatPlugin):
    """Configuration data for the boom boot manager.
    """

    plugin_name = 'boom'
    profiles = ('boot', 'system')

    packages = (
        'lvm2-python-boom',
        'python-boom',
        'python2-boom',
        'python3-boom'
    )

    def setup(self):
        self.add_copy_spec([
            "/boot/boom",
            "/boot/loader/entries",
            "/etc/default/boom",
            "/etc/grub.d/42_boom"
        ])

        self.add_cmd_output([
            "boom list -VV",
            "boom profile list -VV"
        ])

# vim: set et ts=4 sw=4 :
