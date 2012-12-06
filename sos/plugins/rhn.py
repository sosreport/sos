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
import os

class rhn(Plugin, RedHatPlugin):
    """RHN Satellite related information
    """
    satellite = False
    proxy = False

    optionList = [("log", 'gathers all apache logs', 'slow', False)]

    def defaultenabled(self):
        return False

    def rhn_package_check(self):
        self.satellite = self.isInstalled("rhns-satellite-tools") \
                      or self.isInstalled("spacewalk-java") \
                      or self.isInstalled("rhn-base")
        self.proxy = self.isInstalled("rhns-proxy-tools") \
                      or self.isInstalled("spacewalk-proxy-management") \
                      or self.isInstalled("rhn-proxy-management")
        return self.satellite or self.proxy

    def checkenabled(self):
        # enable if any related package is installed
        return self.rhn_package_check()

    def setup(self):
        self.rhn_package_check()
        self.addCopySpecs([
            "/etc/httpd/conf*",
            "/etc/rhn",
            "/var/log/rhn*"])

        if self.getOption("log"):
            self.addCopySpec("/var/log/httpd")

        # all these used to go in $DIR/mon-logs/
        self.addCopySpecs([
            "/opt/notification/var/*.log*",
            "/var/tmp/ack_handler.log*",
            "/var/tmp/enqueue.log*"])

        # monitoring scout logs
        self.addCopySpecs([
            "/home/nocpulse/var/*.log*",
            "/home/nocpulse/var/commands/*.log*",
            "/var/tmp/ack_handler.log*",
            "/var/tmp/enqueue.log*",
            "/var/log/nocpulse/*.log*",
            "/var/log/notification/*.log*",
            "/var/log/nocpulse/TSDBLocalQueue/TSDBLocalQueue.log"])

        self.addCopySpec("/root/ssl-build")
        self.collectExtOutput("/usr/bin/rhn-schema-version", root_symlink = "database-schema-version")
        self.collectExtOutput("/usr/bin/rhn-charsets", root_symlink = "database-character-sets")

        if self.satellite:
            self.addCopySpecs(["/etc/tnsnames.ora", "/etc/jabberd",
                                "/etc/tomcat6/", "/var/log/tomcat6/"])
            if os.path.exists("/usr/bin/spacewalk-debug"):
                self.collectExtOutput("/usr/bin/spacewalk-debug --dir %s"
                        % os.path.join(self.cInfo['dstroot'], "sos_commands/rhn"))

        if self.proxy:
            self.addCopySpecs(["/etc/squid", "/var/log/squid"])
