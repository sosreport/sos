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

from sos.plugintools import PluginBase

class rhn(PluginBase):
    """This plugin gathers RHN server related information
    """
    def setup(self):
        # XXX check for the presence of requisite packages
        satellite = self.cInfo["policy"].pkgByName("rhns-satellite-tools")
        proxy = self.cInfo["policy"].pkgByName("rhns-proxy-tools")
        if not satellite and not proxy:
            return

        #
        # First, grab things needed from both Satellite and Proxy systems
        #
        # TODO: add chain load so we can use existing modules for httpd, &c.
        #

        # basic RHN logs and configs
        self.addCopySpec("/var/log/rhn*")
        self.addCopySpec("/etc/rhn")
        self.collectExtOutput("/usr/share/rhn/up2date_client/hardware.py")

        # httpd
        self.addCopySpec("/etc/httpd/conf")
        self.addCopySpec("/var/log/httpd")

        # RPM manifests
        self.collectExtOutput("/bin/rpm -qa --last | sort")

        # monitoring scout logs
        self.addCopySpec("/home/nocpulse/var/*.log*")
        self.addCopySpec("/home/nocpulse/var/commands/*.log*")

        #
        # Now, go for product-specific data
        #
        if satellite:
            self.setupSatellite(satellite)

        if proxy:
            self.setupProxy(proxy)

    def setupSatellite(self, satellite):
        self.collectExtOutput("/usr/bin/rhn-schema-version")
        self.collectExtOutput("/usr/bin/rhn-charsets")

        # oracle
        self.addCopySpec("/etc/tnsnames.ora")

        # tomcat (4.x and newer satellites only)
        if not self.cInfo["policy"].pkgNVRA(satellite)[1].startswith("3."):
            self.addCopySpec("/etc/tomcat5")
            self.addCopySpec("/var/log/tomcat5")

        # jabberd
        #  - logs to /var/log/messages
        self.addCopySpec("/etc/jabberd")

        # SSL build
        self.addCopySpec("/root/ssl-build")
    
        # monitoring logs
        self.addCopySpec("/opt/notification/var/*.log*")
        self.addCopySpec("/var/tmp/ack_handler.log*")
        self.addCopySpec("/var/tmp/enqueue.log*")

    def setupProxy(self, proxy):
        # squid
        self.addCopySpec("/etc/squid")
        self.addCopySpec("/var/log/squid")
 
