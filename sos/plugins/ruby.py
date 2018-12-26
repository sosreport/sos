# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ruby(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Ruby runtime"""

    plugin_name = 'ruby'
    packages = ('ruby', 'ruby-irb')

    def setup(self):
        self.add_cmd_output([
            'ruby --version',
            'irb --version',
            'gem --version',
            'gem list'
        ])

# vim: set et ts=4 sw=4 :
