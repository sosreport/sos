# Copyright (C) 2023 Canonical Ltd., Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json

from sos.policies.runtimes import ContainerRuntime
from sos.utilities import sos_get_command_output
from sos.utilities import is_executable


class LxdContainerRuntime(ContainerRuntime):
    """Runtime class to use for systems running LXD"""

    name = 'lxd'
    binary = 'lxc'

    def check_is_active(self):
        # the daemon must be running
        if (is_executable('lxc', self.policy.sysroot) and
                self.policy.package_manager.pkg_by_name('lxd') and
                (self.policy.init_system.is_running('lxd') or
                 self.policy.init_system.is_running('snap.lxd.daemon'))):
            self.active = True
            return True
        return False

    def get_containers(self, get_all=False):
        """Get a list of containers present on the system.

        :param get_all: If set, include stopped containers as well
        :type get_all: ``bool``
        """
        containers = []

        _cmd = f"{self.binary} list --format json"
        if self.active:
            out = sos_get_command_output(_cmd, chroot=self.policy.sysroot)

            if out["status"] == 0:
                out_json = json.loads(out["output"])

                for container in out_json:
                    if container['status'] == 'Running' or get_all:
                        # takes the form (container_id, container_name)
                        containers.append(
                            (container['expanded_config']['volatile.uuid'],
                             container['name']))

        return containers

    def get_images(self):
        """Get a list of images present on the system

        :returns: A list of 2-tuples containing (image_name, image_id)
        :rtype: ``list``
        """
        images = []
        if self.active:
            out = sos_get_command_output(
                f"{self.binary} image list --format json",
                chroot=self.policy.sysroot
            )
            if out['status'] == 0:
                out_json = json.loads(out["output"])
                for ent in out_json:
                    # takes the form (image_name, image_id)
                    if 'update_source' in ent:
                        images.append((
                            ent['update_source']['alias'],
                            ent['fingerprint']))
        return images

    def get_volumes(self):
        """Get a list of container volumes present on the system

        :returns: A list of volume IDs on the system
        :rtype: ``list``
        """
        vols = []
        stg_pool = "default"
        if self.active:

            # first get the default storage pool
            out = sos_get_command_output(
                f"{self.binary} profile list --format json",
                chroot=self.policy.sysroot
            )
            if out['status'] == 0:
                out_json = json.loads(out['output'])
                for profile in out_json:
                    if (profile['name'] == 'default' and
                            'root' in profile['devices']):
                        stg_pool = profile['devices']['root']['pool']
                        break

            out = sos_get_command_output(
                f"{self.binary} storage volume list {stg_pool} --format json",
                chroot=self.policy.sysroot
            )
            if out['status'] == 0:
                out_json = json.loads(out['output'])
                for ent in out_json:
                    vols.append(ent['name'])
        return vols

    def get_logs_command(self, container):
        """Get the command string used to dump container logs from the
        runtime

        :param container: The name or ID of the container to get logs for
        :type container: ``str``

        :returns: Formatted runtime command to get logs from `container`
        :type: ``str``
        """
        return f"{self.binary} info {container} --show-log"

    def get_copy_command(self, container, path, dest, sizelimit=None):
        """Generate the command string used to copy a file out of a container
        by way of the runtime.

        :param container:   The name or ID of the container
        :type container:    ``str``

        :param path:        The path to copy from the container. Note that at
                            this time, no supported runtime supports globbing
        :type path:         ``str``

        :param dest:        The destination on the *host* filesystem to write
                            the file to
        :type dest:         ``str``

        :param sizelimit:   Limit the collection to the last X bytes of the
                            file at PATH
        :type sizelimit:    ``int``

        :returns:   Formatted runtime command to copy a file from a container
        :rtype:     ``str``
        """
        if sizelimit:
            return f"{self.run_cmd} {container} tail -c {sizelimit} {path}"
        return f"{self.binary} file pull {container}{path} {dest}"


# vim: set et ts=4 sw=4 :
