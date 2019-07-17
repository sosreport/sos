# Copyright (C) 2019 Cédric Jeanneret <cjeanner@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackContainerImagePrepare(Plugin, RedHatPlugin,
                                     DebianPlugin, UbuntuPlugin):
    """OpenStack container-image-prepare sos plugin."""

    plugin_name = "openstack_container_image_prepare"
    profiles = ('openstack',)
    files = ('/var/log/tripleo-container-image-prepare.log',)

    def setup(self):
        """Gathering the contents of the report."""
        self.add_copy_spec([
            '/var/log/tripleo-container-image-prepare.log'
        ])
