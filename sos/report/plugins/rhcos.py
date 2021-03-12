# Copyright (C) 2019 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class RHCoreOS(Plugin, RedHatPlugin):

    short_desc = 'Red Hat CoreOS'

    plugin_name = 'rhcos'
    packages = ('afterburn', 'redhat-release-coreos')

    def setup(self):
        units = ['coreos-boot-edit', 'coreos-copy-firstboot-network',
                 'coreos-generate-iscsi-initiatorname',
                 'coreos-gpt-setup', 'coreos-teardown-initramfs',
                 'gcp-routes', 'ignition-disks', 'ignition-fetch',
                 'ignition-fetch-offline', 'ignition-files',
                 'ignition-firstboot-complete', 'ignition-mount',
                 'ignition-ostree-growfs', 'ignition-ostree-populate-var',
                 'ignition-remount-system', 'ignition-setup-user']

        for unit in units:
            self.add_journal(unit)

        self.add_cmd_output(
            'afterburn --cmdline --attributes /dev/stdout',
            timeout=60
        )

# vim: set et ts=4 sw=4 :
