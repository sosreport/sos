# Copyright (C) 2019 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class CloudInit(Plugin, IndependentPlugin):

    short_desc = 'cloud-init instance configurations'

    plugin_name = 'cloud_init'
    packages = ('cloud-init',)
    services = ('cloud-init',)

    def setup(self):

        self.add_cmd_output([
            'cloud-init --version',
            'cloud-init features',
            'cloud-init status'
        ])

        self.add_copy_spec([
            '/etc/cloud/',
            '/run/cloud-init/',
            '/var/log/cloud-init*'
        ])

# vim: set et ts=4 sw=4 :
