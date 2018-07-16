# Copyright (C) 2018 Red Hat, Inc.,
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class OvirtNode(Plugin, RedHatPlugin):
    """oVirt Node specific information"""

    packages = (
        'imgbased',
        'ovirt-node-ng-nodectl',
    )

    plugin_name = 'ovirt_node'
    profiles = ('virt',)

    def setup(self):

        # Add log files
        self.add_copy_spec([
            '/var/log/imgbased.log',
            # Required for node versions < 4.2
            '/tmp/imgbased.log',
        ])

        # Collect runtime info
        self.add_cmd_output([
            'imgbase layout',
            'nodectl --machine-readable check',
            'nodectl info',
        ])


# vim: expandtab tabstop=4 shiftwidth=4
