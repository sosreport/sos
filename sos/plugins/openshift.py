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

class Openshift(Plugin, RedHatPlugin):
    '''Openshift related information'''

    plugin_name = "openshift"

    option_list = [("broker", "Gathers broker specific files", "slow", False),
		   ("node", "Gathers node specific files", "slow", False)]

    def setup(self):
	    self.add_copy_specs(["/etc/openshift-enterprise-version",
		    "/etc/openshift/",
                    "/var/log/openshift/",
		    "/etc/dhcp/dhclient-*"])

            self.add_cmd_output("oo-diagnostics")

	    if self.option_enabled("broker"):
		    self.add_copy_specs(["/var/log/activemq/",
				    "/var/log/mongodb/",
        			    "/var/log/mcollective-client.log",
				    "/var/log/openshift/broker/",
				    "/var/log/openshift/console/"])

		    self.add_cmd_output("oo-accept-broker -v")
		    self.add_cmd_output("oo-admin-chk -v")
		    self.add_cmd_output("mco ping")
		    self.add_cmd_output("oo-mco ping")
		    self.add_cmd_output("gem list --local")
		    self.add_cmd_output("scl enable ruby193 'gem list --local'")
		    #self.add_cmd_output("cd /var/www/openshift/broker/ && scl enable ruby193 'bundle --local'")

	    if self.option_enabled("node"):
		    self.add_copy_specs(["/var/log/openshift/node/",
        			    "/cgroup/*/openshift/",
        			    "/var/log/mcollective.log",
        			    "/opt/rh/ruby193/root/etc/mcollective/",
        			    "/var/log/openshift-gears-async-start.log",
        			    "/var/log/httpd/"])

		    self.add_cmd_output("oo-accept-node -v")
		    self.add_cmd_output("oo-admin-ctl-gears list")
		    self.add_cmd_output("ls -l /var/lib/openshift/")

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
