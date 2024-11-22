# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from shlex import quote
from sos.utilities import sos_get_command_output, is_executable


class ContainerRuntime():
    """Encapsulates a container runtime that provides the ability to plugins to
    check runtime status, check for the presence of specific containers, and
    to format commands to run in those containers

    :param policy: The loaded policy for the system
    :type policy: ``Policy()``

    :cvar name: The name of the container runtime, e.g. 'podman'
    :vartype name: ``str``

    :cvar containers: A list of containers known to the runtime
    :vartype containers: ``list``

    :cvar images: A list of images known to the runtime
    :vartype images: ``list``

    :cvar binary: The binary command to run for the runtime, must exit within
                  $PATH
    :vartype binary: ``str``
    """

    name = 'Undefined'
    containers = []
    images = []
    volumes = []
    binary = ''
    active = False

    def __init__(self, policy=None):
        self.policy = policy
        self.run_cmd = f"{self.binary} exec "

    def load_container_info(self):
        """If this runtime is found to be active, attempt to load information
        on the objects existing in the runtime.
        """
        self.containers = self.get_containers()
        self.images = self.get_images()
        self.volumes = self.get_volumes()

    def check_is_active(self):
        """Check to see if the container runtime is both present AND active.

        Active in this sense means that the runtime can be used to glean
        information about the runtime itself and containers that are running.

        :returns: ``True`` if the runtime is active, else ``False``
        :rtype: ``bool``
        """
        if is_executable(self.binary, self.policy.sysroot):
            self.active = True
            return True
        return False

    def check_can_copy(self):
        """Check if the runtime supports copying files out of containers and
        onto the host filesystem
        """
        return True

    def get_containers(self, get_all=False):
        """Get a list of containers present on the system.

        :param get_all: If set, include stopped containers as well
        :type get_all: ``bool``
        """
        containers = []
        _cmd = f"{self.binary} ps {'-a' if get_all else ''}"
        if self.active:
            out = sos_get_command_output(_cmd, chroot=self.policy.sysroot)
            if out['status'] == 0:
                for ent in out['output'].splitlines()[1:]:
                    ent = ent.split()
                    # takes the form (container_id, container_name)
                    containers.append((ent[0], ent[-1]))
        return containers

    def get_container_by_name(self, name):
        """Get the container ID for the container matching the provided
        name

        :param name: The name of the container, note this can be a regex
        :type name: ``str``

        :returns: The id of the first container to match `name`, else ``None``
        :rtype: ``str``
        """
        if not self.active or name is None:
            return None
        for c in self.containers:
            if re.match(name, c[1]):
                return c[0]
        return None

    def get_images(self):
        """Get a list of images present on the system

        :returns: A list of 2-tuples containing (image_name, image_id)
        :rtype: ``list``
        """
        images = []
        fmt = '{{lower .Repository}}:{{lower .Tag}} {{lower .ID}}'
        if self.active:
            out = sos_get_command_output(
                f"{self.binary} images --format '{fmt}'",
                chroot=self.policy.sysroot
            )
            if out['status'] == 0:
                for ent in out['output'].splitlines():
                    ent = ent.split()
                    # takes the form (image_name, image_id)
                    images.append((ent[0], ent[1]))
        return images

    def get_volumes(self):
        """Get a list of container volumes present on the system

        :returns: A list of volume IDs on the system
        :rtype: ``list``
        """
        vols = []
        if self.active:
            out = sos_get_command_output(
                f"{self.binary} volume ls",
                chroot=self.policy.sysroot
            )
            if out['status'] == 0:
                for ent in out['output'].splitlines()[1:]:
                    ent = ent.split()
                    vols.append(ent[-1])
        return vols

    def container_exists(self, container):
        """Check if a given container ID or name exists on the system from the
        perspective of the container runtime.

        Note that this will only check _running_ containers

        :param container:       The name or ID of the container
        :type container:        ``str``

        :returns:               True if the container exists, else False
        :rtype:                 ``bool``
        """
        for _contup in self.containers:
            if container in _contup:
                return True
        return False

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
        return f"{self.run_cmd} {container} {quoted_cmd}"

    def fmt_registry_credentials(self, username, password):
        """Format a string to pass to the 'run' command of the runtime to
        enable authorization for pulling the image during `sos collect`, if
        needed using username and optional password creds

        :param username:    The name of the registry user
        :type username:     ``str``

        :param password:    The password of the registry user
        :type password:     ``str`` or ``None``

        :returns:  The string to use to enable a run command to pull the image
        :rtype:    ``str``
        """
        return f"--creds={username}{':' + password if password else ''}"

    def fmt_registry_authfile(self, authfile):
        """Format a string to pass to the 'run' command of the runtime to
        enable authorization for pulling the image during `sos collect`, if
        needed using an authfile.
        """
        if authfile:
            return f"--authfile {authfile}"
        return ''

    def get_logs_command(self, container):
        """Get the command string used to dump container logs from the
        runtime

        :param container: The name or ID of the container to get logs for
        :type container: ``str``

        :returns: Formatted runtime command to get logs from `container`
        :type: ``str``
        """
        return f"{self.binary} logs -t {container}"

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
        return f"{self.binary} cp {container}:{path} {dest}"

# vim: set et ts=4 sw=4 :
