## Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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
import glob

class openshift(sos.plugintools.PluginBase):
    """OpenShift related information
    """

    optionList = [('gear', 'Collect information about a specific gear',
                        'fast', False)]

    broker_pkg = 'openshift-origin-broker'
    node_pkg = 'rubygem-openshift-origin-node'

    broker = False
    node = False

    packages = [
            broker_pkg,
            node_pkg ]

    def setup(self):
        self.broker = self.isInstalled(self.broker_pkg)
        self.node = self.isInstalled(self.node_pkg)
        self.gear = self.getOption('gear')

        self.addCopySpec("/etc/openshift")
        self.addForbiddenPath("/etc/openshift/rsync_id_rsa")

        if self.broker:
            self.addCopySpec("/var/www/openshift/broker/httpd/logs/*")
            self.addCopySpec("/var/www/openshift/broker/log/*.log")
            self.addCopySpec("/var/log/openshift/user_action.log")
            self.collectExtOutput("/usr/sbin/oo-accept-broker -v")
            self.collectExtOutput("/usr/sbin/oo-admin-chk")
            self.collectExtOutput("/usr/sbin/mco ping")
            self.collectExtOutput("/usr/bin/gem list --local")
            self.collectExtOutput("sh -c 'cd /var/www/openshift/broker/ "
                                + "&& /usr/bin/bundle --local'",
                                suggest_filename =
                                "cd_var_www_openshift_broker-bundle_--local")
        if self.node:
            self.addCopySpec("/cgroup/all/openshift")
            self.addCopySpec("/var/log/mcollective.log")
            self.addCopySpec("/var/log/openshift-gears-async-start.log")
            # this file is not considered sensitive on openshift
            # node installations.
            self.addCopySpec("/etc/passwd")
            self.collectExtOutput("/usr/sbin/oo-accept-node")
            self.collectExtOutput("/usr/sbin/oo-admin-ctl-gears list")
            self.collectExtOutput("/bin/ls /var/lib/openshift")
            if self.gear:
                gear_path = glob.glob("/var/lib/openshift/%s*" % self.gear)[0]
                self.collectExtOutput("/bin/ls %s" % gear_path)
                self.addCopySpec(gear_path + "/*/log*")
        try:
            status, output, runtime = self.callExtProg("/bin/hostname")
            if status != 0:
                hostname = None
            else:
                hostname = output.strip()
        except:
            hostname = None
        self.collectExtOutput("/usr/bin/dig %s axfr" % hostname)
        return

    def postproc(self):
        self.doRegexSub("/etc/openshift/htpasswd", r"(\s*:).*", r"\1******")
