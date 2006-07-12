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
    def collect(self):
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
        self.copyFileGlob("/var/log/rhn*")
        self.copyFileOrDir("/etc/rhn")
        self.runExe("/usr/share/rhn/up2date_client/hardware.py")

        # httpd
        self.copyFileOrDir("/etc/httpd/conf")
        self.copyFileOrDir("/var/log/httpd")

        # RPM manifests
        self.runExe("/bin/rpm -qa --last | sort")

        # monitoring scout logs
        self.copyFileGlob("/home/nocpulse/var/*.log*")
        self.copyFileGlob("/home/nocpulse/var/commands/*.log*")

        #
        # Now, go for product-specific data
        #
        if satellite:
            self.collectSatellite(satellite)

        if proxy:
            self.collectProxy(proxy)

    def collectSatellite(self, satellite):
        self.runExe("/usr/bin/rhn-schema-version")
        self.runExe("/usr/bin/rhn-charsets")

        # oracle
        self.copyFileOrDir("/etc/tnsnames.ora")

        # tomcat (4.x and newer satellites only)
        if not self.cInfo["policy"].pkgNVRA(satellite)[1].startswith("3."):
            self.copyFileOrDir("/etc/tomcat5")
            self.copyFileOrDir("/var/log/tomcat5")

        # jabberd
        #  - logs to /var/log/messages
        self.copyFileOrDir("/etc/jabberd")

        # SSL build
        self.copyFileOrDir("/root/ssl-build")
    
        # monitoring logs
        self.copyFileGlob("/opt/notification/var/*.log*")
        self.copyFileGlob("/var/tmp/ack_handler.log*")
        self.copyFileGlob("/var/tmp/enqueue.log*")

    def collectProxy(self, proxy):
        # squid
        self.copyFileOrDir("/etc/squid")
        self.copyFileOrDir("/var/log/squid")
 
