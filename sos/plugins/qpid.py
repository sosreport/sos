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


class Qpid(Plugin, RedHatPlugin):
    """Qpid messaging
    """

    plugin_name = 'qpid'
    profiles = ('services',)

    packages = ('qpidd', 'qpid-cpp-server', 'qpid-tools')
    option_list = [("port", "listening port to connect to", '', ""),
                   ("ssl-certificate",
                    "Path to file containing client SSL certificate", '', ""),
                   ("ssl-key",
                    "Path to file containing client SSL private key", '', ""),
                   ("ssl", "enforce SSL / amqps connection", '', False)]

    def setup(self):
        """ performs data collection for qpid broker """
        options = ""
        amqps_prefix = ""  # set amqps:// when SSL is used
        if self.get_option("ssl"):
            amqps_prefix = "amqps://"
        # for either present option, add --option=value to 'options' variable
        for option in ["ssl-certificate", "ssl-key"]:
            if self.get_option(option):
                amqps_prefix = "amqps://"
                options = (options + " --%s=" % (option) +
                           self.get_option(option))
        if self.get_option("port"):
            options = (options + " -b " + amqps_prefix +
                       "localhost:%s" % (self.get_option("port")))

        self.add_cmd_output([
            "qpid-stat -g" + options,  # applies since 0.18 version
            "qpid-stat -b" + options,  # applies to pre-0.18 versions
            "qpid-stat -c" + options,
            "qpid-stat -e" + options,
            "qpid-stat -q" + options,
            "qpid-stat -u" + options,
            "qpid-stat -m" + options,  # applies since 0.18 version
            "qpid-config exchanges" + options,
            "qpid-config queues" + options,
            "qpid-config exchanges -b" + options,  # applies to pre-0.18 vers.
            "qpid-config queues -b" + options,  # applies to pre-0.18 versions
            "qpid-config exchanges -r" + options,  # applies since 0.18 version
            "qpid-config queues -r" + options,  # applies since 0.18 version
            "qpid-route link list" + options,
            "qpid-route route list" + options,
            "qpid-cluster" + options,  # applies to pre-0.22 versions
            "qpid-ha query" + options,  # applies since 0.22 version
            "ls -lanR /var/lib/qpidd"
        ])

        self.add_copy_spec([
            "/etc/qpidd.conf",  # applies to pre-0.22 versions
            "/etc/qpid/qpidd.conf",  # applies since 0.22 version
            "/var/lib/qpid/syslog",
            "/etc/ais/openais.conf",
            "/var/log/cumin.log",
            "/var/log/mint.log",
            "/etc/sasl2/qpidd.conf",
            "/etc/qpid/qpidc.conf",
            "/etc/sesame/sesame.conf",
            "/etc/cumin/cumin.conf",
            "/etc/corosync/corosync.conf",
            "/var/lib/sesame",
            "/var/log/qpidd.log",
            "/var/log/sesame",
            "/var/log/cumin"
        ])

# vim: set et ts=4 sw=4 :
