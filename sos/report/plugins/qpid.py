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
                options = f"{options} --{option}={self.get_option(option)}"
        if self.get_option("port"):
            options = (f"{options} -b {amqps_prefix}"
                       f'localhost:{self.get_option("port")}')

        self.add_cmd_output([
            f"qpid-stat -g{options}",
            f"qpid-stat -b{options}",
            f"qpid-stat -c{options}",
            f"qpid-stat -e{options}",
            f"qpid-stat -q{options}",
            f"qpid-stat -u{options}",
            f"qpid-stat -m{options}",
            f"qpid-config exchanges{options}",
            f"qpid-config queues{options}",
            f"qpid-config exchanges -b{options}",
            f"qpid-config queues -b{options}",
            f"qpid-config exchanges -r{options}",
            f"qpid-config queues -r{options}",
            f"qpid-route link list{options}",
            f"qpid-route route list{options}",
            f"qpid-cluster{options}",
            f"qpid-ha query{options}",
            "ls -lanR /var/lib/qpidd",
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
