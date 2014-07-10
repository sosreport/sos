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

import sos.plugintools
import os.path

class openshift(sos.plugintools.PluginBase):
    '''Openshift related information'''

    # The 'broker' and 'node' options are obsolete but are maintained
    # here for compatibility with external programs that call sosreport
    # with these names.
    optionList = [
        ("broker", "Gathers broker specific files", "slow", False),
        ("node", "Gathers node specific files", "slow", False),
        ("gear", "Collect information about a specific gear", "fast", False)
    ]

    ruby = "ruby193"
    vendor ="rh"

    def is_broker(self):
        return os.path.exists("/etc/openshift/broker.conf")

    def is_node(self):
        return os.path.exists("/etc/openshift/node.conf")

    def setup(self):
        self.gear = self.getOption('gear')
        self.addCopySpecs([
            "/etc/openshift-enterprise-release",
            "/var/log/openshift/",
            "/etc/openshift/*.conf",
            "/etc/openshift/upgrade/",
        ])

        self.collectExtOutput("oo-diagnostics -v")

        if self.is_broker():
            self.addCopySpecs([
                "/etc/openshift/quickstarts.json",
                "/etc/openshift/plugins.d/*.conf",
                "/var/www/openshift/broker/httpd/conf.d/*.conf",
                "/var/www/openshift/console/httpd/conf.d/*.conf",
            ])

            self.collectExtOutputs([
                "oo-accept-broker -v",
                "oo-admin-chk -v",
                "oo-mco ping",
            ])

        if self.is_node():
            self.addCopySpecs([
                "/etc/openshift/node-plugins.d/*.conf",
                "/etc/openshift/cart.conf.d/",
                "/etc/openshift/env/",
                "/cgroup/*/openshift",
                "/opt/%s/%s/root/etc/mcollective/" % (self.vendor, self.ruby),
                "/var/log/httpd/openshift_log",
                "/var/log/mcollective.log",
                "/var/log/node-web-proxy/access.log",
                "/var/log/node-web-proxy/error.log",
                "/var/log/node-web-proxy/websockets.log",
                "/var/log/node-web-proxy/supervisor.log",
            ])


            self.collectExtOutputs([
                "oo-accept-node -v",
                "oo-admin-ctl-gears list",
                "ls -laZ /var/lib/openshift"
            ])

            if self.gear:
                gear_path = glob.glob("/var/lib/openshift/%s*" % self.gear)[0]
                self.collectExtOutput("/bin/ls %s" % gear_path)
                self.addCopySpec(gear_path + "/*/log*")

    def postproc(self):
        self.doRegexSub('/etc/openshift/broker.conf',
                r"(MONGO_PASSWORD=)(.*)",
                r"\1*******")

        self.doRegexSub('/etc/openshift/broker.conf',
                r"(SESSION_SECRET=)(.*)",
                r"\1*******")

        self.doRegexSub('/etc/openshift/console.conf',
                r"(SESSION_SECRET=)(.*)",
                r"\1*******")

        self.doRegexSub("/opt/%s/%s/root/etc/mcollective/server.cfg" % (self.vendor, self.ruby),
                r"(.*\.password.?=)(.*)",
                r"\1********")

# vim: et ts=4 sw=4
