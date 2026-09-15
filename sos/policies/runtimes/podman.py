# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.runtimes import ContainerRuntime


class PodmanContainerRuntime(ContainerRuntime):
    """Runtime class to use for systems running Podman"""

    name = 'podman'
    binary = 'podman'

    def get_info_command(self, run_debug=False):
        """Return the command to gather runtime-wide information from podman

        :param run_debug: If True, add the --debug flag to the command
        :type run_debug: ``bool``

        :returns: Formatted runtime info command
        :rtype: ``str``
        """
        if run_debug:
            return f"{self.binary} info --debug"
        return f"{self.binary} info"

    def get_list_command(self, get_all=False):
        """Return the command to run to get a list of containers known to the
        runtime, formatted as json

        Note that the system-level runtime already collects this information
        for the root user when it is loaded. This method exists so that
        plugins collecting from a non-root (rootless) user's runtime can
        build the equivalent command and run it with ``runas=<user>``, since
        the runtime's cached list only reflects the root instance.

        :param get_all: If True, return all containers, otherwise only return
                        running containers
        :type get_all: ``bool``

        :returns: Formatted runtime command to list containers as json
        :rtype: ``str``
        """
        all_flag = '-a' if get_all else ''
        return f"{self.binary} ps {all_flag} --format json"

    def get_inspect_command(self, *containers):
        """Return the command used to inspect one or more containers

        Multiple containers are inspected in a single runtime invocation,
        avoiding one call per container

        :param containers: One or more names of containers to inspect
        :type containers: ``tuple``

        :returns: Formatted inspect command
        :rtype: ``str``
        """
        if not containers:
            return ""
        return f"{self.binary} inspect {' '.join(containers)}"

    def get_exec_command(self, container, cmd):
        """Return the command used to run `cmd` inside a single container

        :param container: The name of the container to execute the command in
        :type container: ``str``

        :param cmd: The command to run inside the container
        :type cmd: ``str``

        :returns: Formatted exec command
        :rtype: ``str``
        """
        return f"{self.run_cmd} {container} {cmd}"

    def get_secrets_command(self):
        """Returns the podman secrets known to the runtime

        :returns: Formatted podman secrets list
        :rtype: ``str``
        """
        return f"{self.binary} secret ls"

    def get_networks_command(self):
        """Returns a list of podman networks known to the runtime

        :returns: Formatted podman network list
        :rtype: ``str``
        """
        return f"{self.binary} network ls"

    def get_volumes_command(self):
        """Returns a list of podman volumes known to the runtime

        :returns: Formatted podman volume list
        :rtype: ``str``
        """
        return f"{self.binary} volume ls"

    def get_stats_command(self):
        """Returns the resource usage statistics for all containers
        known to the runtime, without streaming.

        :returns: Formatted podman containers stats
        :rtype: ``str``
        """
        return f"{self.binary} stats --no-stream --all"

    def get_images_command(self, include_digests=False):
        """Returns the list of podman images known to the runtime

        :param include_digests: If True, add the container digest
                                information in the output
        :type include_digests: ``bool``

        :returns: Formatted podman images list
        :rtype: ``str``
        """
        if include_digests:
            return f"{self.binary} images --digests"
        return f"{self.binary} images"

    def get_system_df_command(self):
        """Return the disk usage of the runtime's storage, broken
        down per image, container and volume

        :returns: Formatted podman storage disk usage
        :rtype: ``str``
        """
        return f"{self.binary} system df -v"

    def get_networks_inspect(self, *networks):
        """Returns the inspect of one or more podman networks

        Multiple networks are inspected in a single runtime
        invocation, avoiding one call per network

        :param networks: One or more names of the networks to inspect
        :type networks: ``tuple``

        :returns: Formatted podman inspect networks
        :rtype: ``str``
        """
        return f"{self.binary} network inspect {' '.join(networks)}"

    def get_volumes_inspect(self, *volumes):
        """Return the inspect of one or more podman volumes

        Multiple volumes are inspected in a single runtime
        invocation, avoiding one call per volume

        :param volumes: One or more names of the networks to inspect
        :type volumes: ``tuple``

        :returns: Formatted podman inspect volumes
        :rtype: ``str``
        """
        return f"{self.binary} volume inspect {' '.join(volumes)}"

# vim: set et ts=4 sw=4 :
