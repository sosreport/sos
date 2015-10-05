# Copyright (C) 2015 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
from socket import gethostname


class QpidDispatch(Plugin, RedHatPlugin):
    """Qpid dispatch router
    """

    plugin_name = 'qpid_dispatch'
    profiles = ('services',)

    packages = ('qdrouterd', 'qpid-dispatch-tools', 'qpid-dispatch-router')
    option_list = [("port", "listening port to connect to", '', ""),
                   ("ssl-certificate",
                    "Path to file containing client SSL certificate", '', ""),
                   ("ssl-key",
                    "Path to file containing client SSL private key", '', ""),
                   ("ssl-trustfile", "trusted CA database file", '', "")]

    def setup(self):
        """ performs data collection for qpid dispatch router """
        options = ""
        if self.get_option("port"):
            options = (options + " -b " + gethostname() +
                       ":%s" % (self.get_option("port")))
        # gethostname() is due to DISPATCH-156

        # for either present option, add --option=value to 'options' variable
        for option in ["ssl-certificate", "ssl-key", "ssl-trustfile"]:
            if self.get_option(option):
                options = (options + " --%s=" % (option) +
                           self.get_option(option))

        self.add_cmd_output([
            "qdstat -a" + options,  # Show Router Addresses
            "qdstat -n" + options,  # Show Router Nodes
            "qdstat -c" + options,  # Show Connections
            "qdstat -m" + options   # Show Broker Memory Stats
        ])

        self.add_copy_spec([
            "/etc/qpid-dispatch/qdrouterd.conf"
        ])

# vim: et ts=4 sw=4
