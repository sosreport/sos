# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
from sos.utilities import sos_get_command_output


class InitSystem():
    """Encapsulates an init system to provide service-oriented functions to
    sos.

    This should be used to query the status of services, such as if they are
    enabled or disabled on boot, or if the service is currently running.

    :param init_cmd: The binary used to interact with the init system
    :type init_cmd: ``str``

    :param list_cmd: The list subcmd given to `init_cmd` to list services
    :type list_cmd: ``str``

    :param query_cmd: The query subcmd given to `query_cmd` to query the
                      status of services
    :type query_cmd: ``str``

    :param chroot:  Location to chroot to for any command execution, i.e. the
                    sysroot if we're running in a container
    :type chroot:   ``str`` or ``None``

    """

    def __init__(self, init_cmd=None, list_cmd=None, query_cmd=None,
                 chroot=None):
        """Initialize a new InitSystem()"""

        self.services = {}

        self.init_cmd = init_cmd
        self.list_cmd = "%s %s" % (self.init_cmd, list_cmd) or None
        self.query_cmd = "%s %s" % (self.init_cmd, query_cmd) or None
        self.chroot = chroot

    def is_enabled(self, name):
        """Check if given service name is enabled

        :param name: The name of the service
        :type name: ``str``

        :returns: ``True`` if the service is enabled, else ``False``
        :rtype: ``bool``
        """
        if self.services and name in self.services:
            return self.services[name]['config'] == 'enabled'
        return False

    def is_disabled(self, name):
        """Check if a given service name is disabled
        :param name: The name of the service
        :type name: ``str``

        :returns: ``True`` if the service is disabled, else ``False``
        :rtype: ``bool``
        """
        if self.services and name in self.services:
            return self.services[name]['config'] == 'disabled'
        return False

    def is_service(self, name):
        """Checks if the given service name exists on the system at all, this
        does not check for the service status

        :param name: The name of the service
        :type name: ``str``

        :returns: ``True`` if the service exists, else ``False``
        :rtype: ``bool``
        """
        return name in self.services

    def is_running(self, name, default=True):
        """Checks if the given service name is in a running state.

        This should be overridden by initsystems that subclass InitSystem

        :param name: The name of the service
        :type name: ``str``

        :param default: The default response in case the check fails
        :type default:  ``bool`

        :returns: ``True`` if the service is running, else ``default``
        :rtype: ``bool``
        """
        # This is going to be primarily used in gating if service related
        # commands are going to be run or not. Default to always returning
        # True when an actual init system is not specified by policy so that
        # we don't inadvertantly restrict sosreports on those systems
        return default

    def load_all_services(self):
        """This loads all services known to the init system into a dict.
        The dict should be keyed by the service name, and contain a dict of the
        name and service status

        This must be overridden by anything that subclasses `InitSystem` in
        order for service methods to function properly
        """
        pass

    def _query_service(self, name):
        """Query an individual service"""
        if self.query_cmd:
            try:
                return sos_get_command_output(
                    "%s %s" % (self.query_cmd, name),
                    chroot=self.chroot
                )
            except Exception:
                return None
        return None

    def parse_query(self, output):
        """Parses the output returned by the query command to make a
        determination of what the state of the service is

        This should be overriden by anything that subclasses InitSystem

        :param output: The raw output from querying the service with the
                       configured `query_cmd`
        :type output: ``str``

        :returns: A state for the service, e.g. 'active', 'disabled', etc...
        :rtype: ``str``
        """
        return output

    def get_service_names(self, regex):
        """Get a list of all services discovered on the system that match the
        given regex.

        :param regex: The service name regex to match against
        :type regex: ``str``
        """
        reg = re.compile(regex, re.I)
        return [s for s in self.services.keys() if reg.match(s)]

    def get_service_status(self, name):
        """Get the status for the given service name along with the output
        of the query command

        :param name: The name of the service
        :type name: ``str``

        :returns: Service status and query_cmd output from the init system
        :rtype: ``dict`` with keys `name`, `status`, and `output`
        """
        _default = {
            'name': name,
            'status': 'missing',
            'output': ''
        }
        if name not in self.services:
            return _default
        if 'status' in self.services[name]:
            # service status has been queried before, return existing info
            return self.services[name]
        svc = self._query_service(name)
        if svc is not None:
            self.services[name]['status'] = self.parse_query(svc['output'])
            self.services[name]['output'] = svc['output']
            return self.services[name]
        return _default


# vim: set et ts=4 sw=4 :
