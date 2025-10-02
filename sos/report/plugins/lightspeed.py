# Copyright (C) 2025 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Lightspeed(Plugin, RedHatPlugin):

    short_desc = 'Lightspeed Command Line Assistant'

    plugin_name = 'lightspeed'
    profiles = ('ai',)
    services = ('clad',)

    def setup(self):
        self.add_copy_spec("/etc/xdg/command-line-assistant/config.toml")

# vim: set et ts=4 sw=4 :
