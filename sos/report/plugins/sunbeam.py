# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Sunbeam(Plugin, UbuntuPlugin):

    short_desc = "Sunbeam Openstack Controller"

    plugin_name = "sunbeam"
    profiles = ('cloud',)
    packages = ('openstack',)

    common_dir = '/var/snap/openstack/common'

    def setup(self):

        self.add_service_status('snap.openstack.*')

        self.add_copy_spec([
            f'{self.common_dir}/hooks.log',
            f'{self.common_dir}/state/daemon.yaml',
            f'{self.common_dir}/state/truststore/sunbeam.maas.yaml',
            f'{self.common_dir}/state/database/info.yaml',
            f'{self.common_dir}/state/database/cluster.yaml',
            '/var/snap/openstack/current/config.yaml',
        ])

        self.add_cmd_output([
            'sunbeam cluster list',
            'sunbeam cluster list --format yaml',
        ])

    def postproc(self):

        self.do_file_private_sub(
            f'{self.common_dir}/state/truststore/sunbeam.maas.yaml'
        )

# vim: et ts=4 sw=4
