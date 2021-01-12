# Copyright (C) 2021 Red Hat, Inc., Lev Veyde <lveyde@redhat.com>
# Copyright (C) 2018 Red Hat, Inc.,
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OvirtNode(Plugin, RedHatPlugin):

    short_desc = 'oVirt Node specific information'

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

        certificates = [
            '/etc/pki/vdsm/certs/cacert.pem',
            '/etc/pki/vdsm/certs/vdsmcert.pem',
            '/etc/pki/vdsm/libvirt-spice/ca-cert.pem',
            '/etc/pki/vdsm/libvirt-spice/server-cert.pem',
            '/etc/pki/vdsm/libvirt-vnc/ca-cert.pem',
            '/etc/pki/vdsm/libvirt-vnc/server-cert.pem',
        ]

        # Collect runtime info
        self.add_cmd_output([
            'imgbase layout',
            'nodectl --machine-readable check',
            'nodectl info',
        ])

        # Collect certificate info
        self.add_cmd_output([
            'openssl x509 -in %s -text -noout' % c for c in certificates
        ])


# vim: expandtab tabstop=4 shiftwidth=4
