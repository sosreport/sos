# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class Qpid(Plugin, RedHatPlugin):

    short_desc = 'Qpid messaging'

    plugin_name = 'qpid'
    profiles = ('services',)

    packages = ('qpidd', 'qpid-cpp-server', 'qpid-tools')
    option_list = [
        PluginOpt('port', default='', val_type=int,
                  desc='listening port to connect to'),
        PluginOpt('ssl-certificate', default='', val_type=str,
                  desc='Path to file containing client SSL certificate'),
        PluginOpt('ssl-key', default='', val_type=str,
                  desc='Path to file containing client SSL private key'),
        PluginOpt('ssl', default=False, desc='enforce SSL amqps connection')
    ]

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
            "/var/lib/qpidd/.qpidd/qls/dat2/DB_CONFIG",
            "/var/lib/qpidd/qls/dat2/DB_CONFIG",
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
