# Copyright (C) 2019 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Sosreport(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Sos plugin collects information about SoS report itself
    """

    plugin_name = 'sos'

    def setup(self):
        self.add_copy_spec([
            '/etc/sos.conf',
            '/etc/sos.extras.d'
        ])


# vim: et ts=4 sw=4
