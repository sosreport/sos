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

    def info_command(self, run_debug=False):
        """Return the command to list all containers known to the runtime,
        including stopped containers,

        :param run_debug: If True, add the --debug flag to the command
        :type run_debug: ``bool``
        """
        if run_debug:
            return f"{self.binary} info --debug"
        return f"{self.binary} info"

    def list_command(self, get_all=False, list_fmt=None):
        """Return the command to run to get a list of containers known to the
        runtime

        :param get_all: If True, return all containers, otherwise only return
                        running containers
        :type get_all: ``bool``

        :param list_fmt: If set, return the command to run in a format that
                         will be parsed by the sosreport plugin, defaults to
                         `json`.
        :type list_fmt: ``str`` or ``None``

        :returns: Formatted runtime command to list containers in the requested
                  format
        :rtype: ``str``
        """
        if list_fmt is not None:
            return f"{self.binary} ps {'-a' if get_all else ''} --format {list_fmt}"
        return f"{self.binary} ps {'-a' if get_all else ''} --format json"

    def inspect_command(self, container):
        """Return the command used to inspect a single container

        :param container: The name of the container to inspect
        :type container: ``str``

        :returns: Formatted inspect command
        :rtype: ``str``
        """
        return f"{self.binary} inspect {container}"

    def exec_command(self, container, cmd):
        """Return the command used to run `cmd` inside a single container

        :param container: The name of the container to execute the command in
        :type container: ``str``

        :param cmd: The command to run inside the container
        :type cmd: ``str``

        :returns: Formatted exec command
        :rtype: ``str``
        """
        return f"{self.binary} exec {container} {cmd}"

# vim: set et ts=4 sw=4 :
