# Copyright (C) 2021 Red Hat, Inc., Nadia Pinaeva <npinaeva@redhat.com>

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
from pipes import quote


class CrioContainerRuntime(ContainerRuntime):
    """Runtime class to use for systems running crio"""

    name = 'crio'
    binary = 'crictl'

    def check_can_copy(self):
        return False

    def get_containers(self, get_all=False):
        """Get a list of containers present on the system.

        :param get_all: If set, include stopped containers as well
        :type get_all: ``bool``
        """
        containers = []
        _cmd = "%s ps %s -o json" % (self.binary, '-a' if get_all else '')
        if self.active:
            out = sos_get_command_output(_cmd, chroot=self.policy.sysroot)
            if out["status"] == 0:
                out_json = json.loads(out["output"])
                for container in out_json["containers"]:
                    # takes the form (container_id, container_name)
                    containers.append(
                        (container["id"], container["metadata"]["name"]))
        return containers

    def get_images(self):
        """Get a list of images present on the system

        :returns: A list of 2-tuples containing (image_name, image_id)
        :rtype: ``list``
        """
        images = []
        if self.active:
            out = sos_get_command_output("%s images -o json" % self.binary,
                                         chroot=self.policy.sysroot)
            if out['status'] == 0:
                out_json = json.loads(out["output"])
                for image in out_json["images"]:
                    # takes the form (repository:tag, image_id)
                    if len(image["repoTags"]) > 0:
                        for repo_tag in image["repoTags"]:
                            images.append((repo_tag, image["id"]))
                    else:
                        if len(image["repoDigests"]) == 0:
                            image_name = "<none>"
                        else:
                            image_name = image["repoDigests"][0].split("@")[0]
                        images.append((image_name + ":<none>", image["id"]))
        return images

    def fmt_container_cmd(self, container, cmd, quotecmd):
        """Format a command to run inside a container using the runtime

        :param container: The name or ID of the container in which to run
        :type container: ``str``

        :param cmd: The command to run inside `container`
        :type cmd: ``str``

        :param quotecmd: Whether the cmd should be quoted.
        :type quotecmd: ``bool``

        :returns: Formatted string to run `cmd` inside `container`
        :rtype: ``str``
        """
        if quotecmd:
            quoted_cmd = quote(cmd)
        else:
            quoted_cmd = cmd
        container_id = self.get_container_by_name(container)
        return "%s %s %s" % (self.run_cmd, container_id,
                             quoted_cmd) if container_id is not None else ''

# vim: set et ts=4 sw=4 :
