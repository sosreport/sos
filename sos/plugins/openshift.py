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

    plugin_name = "Openshift"

    option_list = [("broker", "Gathers broker specific files", "slow", False),
		   ("node", "Gathers node specific files", "slow", False)]

    def setup(self):
	    self.add_copy_specs(["/etc/openshift-enterprise-version",
		              "/etc/openshift/"])

	    if self.option_enabled("broker"):
		    self.add_copy_specs(["/var/log/activemq",
				    "/var/log/mongodb",
				    "/var/log/openshift",
				    "/var/www/openshift/broker/log",
				    "/var/www/openshift/broker/httpd/logs/",
				    "/var/log/openshift/user_action.log"])

		    self.collectExtOuput("bin/oo-accpet-broker -v")

	    if self.option_enabled("node"):
		    self.add_copy_spec("/var/log/openshift/node")

		    self.collectExtOuput("bin/oo-accept-node -v")
