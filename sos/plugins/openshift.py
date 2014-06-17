### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os.path

class Openshift(Plugin, RedHatPlugin):
    '''Openshift related information'''

    plugin_name = "openshift"

    # The 'broker' and 'node' options are obsolete but are maintained
    # here for compatibility with external programs that call sosreport
    # with these names.
    option_list = [("broker", "Gathers broker specific files", "slow", False),
           ("node", "Gathers node specific files", "slow", False)]

    ruby = "ruby193"
    vendor ="rh"

    def is_broker(self):
        return os.path.exists("/etc/openshift/broker.conf")

    def is_node(self):
        return os.path.exists("/etc/openshift/node.conf")

    def setup(self):
        self.add_copy_specs([
            "/etc/openshift-enterprise-*",
            "/var/log/openshift/",
            "/etc/openshift/"
        ])

        self.add_cmd_output("oo-diagnostics")

        if self.is_broker():
            self.add_copy_specs([
                "/var/log/mcollective-client.log",
                "/var/log/openshift/broker/",
                "/var/log/openshift/console/"
            ])

            self.add_cmd_outputs([
                "oo-accept-broker -v",
                "oo-admin-chk -v",
                "mco ping",
                "oo-mco ping",
            ])

        if self.is_node():
            self.add_copy_specs([
                "/cgroup/*/openshift",
                "/opt/%s/%s/root/etc/mcollective/" % (self.vendor, self.ruby),
                "/var/log/httpd/openshift_log",
                "/var/log/openshift/node/",
                "/var/log/mcollective.log",
                "/var/log/openshift-gears-async-start.log",
            ])


            self.add_cmd_outputs([
                "oo-accept-node -v",
                "oo-admin-ctl-gears list",
                "ls -l /var/lib/openshift"
            ])

    def postproc(self):
        self.do_file_sub('/etc/openshift/broker.conf',
                r"(MONGO_PASSWORD=)(.*)",
                r"\1*******")

        self.do_file_sub('/etc/openshift/broker.conf',
                r"(SESSION_SECRET=)(.*)",
                r"\1*******")

        self.do_file_sub('/etc/openshift/console.conf',
                r"(SESSION_SECRET=)(.*)",
                r"\1*******")

        self.do_file_sub('/etc/openshift/htpasswd',
                r"(.*:)(.*)",
                r"\1********")

# vim: et ts=4 sw=4
