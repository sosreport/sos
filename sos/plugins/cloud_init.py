# Copyright (C) 2019 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class CloudInit(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """cloud-init instance configurations
    """

    plugin_name = 'cloud_init'
    packages = ('cloud-init',)
    services = ('cloud-init',)

    def setup(self):
        self.add_copy_spec([
            '/var/lib/cloud/',
            '/etc/cloud/',
            '/run/cloud-init/cloud-init-generator.log',
            '/var/log/cloud-init*'
        ])

# vim: set et ts=4 sw=4 :
