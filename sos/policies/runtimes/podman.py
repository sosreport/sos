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
        runtime formatted as json

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

    def get_inspect_command(self, container):
        """Return the command used to inspect a single container

        :param container: The name of the container to inspect
        :type container: ``str``

        :returns: Formatted inspect command
        :rtype: ``str``
        """
        return f"{self.binary} inspect {container}"

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

# vim: set et ts=4 sw=4 :
