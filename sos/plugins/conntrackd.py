# Copyright (C) 2017 Red Hat, Inc., Marcus Linden <mlinden@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
    SuSEPlugin


class Conntrackd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, SuSEPlugin):
    """conntrackd - netfilter connection tracking user-space daemon
    """

    plugin_name = 'conntrackd'
    profiles = ('network', 'cluster')

    packages = ('conntrack-tools', 'conntrackd')

    def setup(self):
        self.add_copy_spec("/etc/conntrackd/conntrackd.conf")
        self.add_cmd_output([
            "conntrackd -s network",
            "conntrackd -s cache",
            "conntrackd -s runtime",
            "conntrackd -s link",
            "conntrackd -s rsqueue",
            "conntrackd -s queue",
            "conntrackd -s ct",
            "conntrackd -s expect",
        ])

# vim: set et ts=4 sw=4 :
