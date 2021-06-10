# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Cockpit(Plugin, IndependentPlugin):

    short_desc = 'Cockpit Web Service'

    plugin_name = 'cockpit'
    packages = ('cockpit-ws', 'cockpit-system')
    services = ('cockpit',)

    def setup(self):
        self.add_copy_spec([
            '/etc/cockpit/cockpit.conf',
            '/etc/pam.d/cockpit'
        ])

        self.add_cmd_output('remotectl certificate')

# vim: set et ts=4 sw=4 :
