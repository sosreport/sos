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
import os

class rhn(sos.plugintools.PluginBase):
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
        return (self.satellite or self.proxy)


    def checkenabled(self):
        # enable if any related package is installed
        return self.rhn_package_check()

    def setup(self):
        self.rhn_package_check()
        self.addCopySpec("/etc/httpd/conf*")
        self.addCopySpec("/etc/rhn")
        self.addCopySpec("/etc/sysconfig/rhn")
        if self.getOption("log"):
            self.addCopySpec("/var/log/httpd")  # httpd-logs
        self.addCopySpec("/var/log/rhn*")   # rhn-logs

        # all these used to go in $DIR/mon-logs/
        self.addCopySpec("/opt/notification/var/*.log*")
        self.addCopySpec("/var/tmp/ack_handler.log*")
        self.addCopySpec("/var/tmp/enqueue.log*")

        # monitoring scout logs
        self.addCopySpec("/home/nocpulse/var/*.log*")
        self.addCopySpec("/home/nocpulse/var/commands/*.log*")
        self.addCopySpec("/var/tmp/ack_handler.log*")
        self.addCopySpec("/var/tmp/enqueue.log*")
        self.addCopySpec("/var/log/nocpulse/*.log*")
        self.addCopySpec("/var/log/notification/*.log*")
        self.addCopySpec("/var/log/nocpulse/TSDBLocalQueue/TSDBLocalQueue.log")

        self.addCopySpec("/root/ssl-build")
        self.collectExtOutput("rpm -qa --last", symlink = "rpm-manifest")
        self.collectExtOutput("/usr/bin/rhn-schema-version", symlink = "database-schema-version")
        self.collectExtOutput("/usr/bin/rhn-charsets", symlink = "database-character-sets")

        if self.satellite:
            if os.path.exists("/usr/bin/spacewalk-debug"):
                self.collectExtOutput("/usr/bin/spacewalk-debug --dir %s"
                        % os.path.join(self.cInfo['dstroot'], "sos_commands/rhn"))
            self.addCopySpec("/etc/tnsnames.ora")   
            self.addCopySpec("/etc/jabberd")

            self.addCopySpec("/etc/tomcat6/")
            self.addCopySpec("/var/log/tomcat6/")

        if self.proxy:
            # copying configuration information
            self.addCopySpec("/etc/squid/")

            # copying logs
            self.addCopySpec("/var/log/squid/")

        return

#    def diagnose(self):
        # RHN Proxy:
        # * /etc/sysconfig/rhn/systemid is owned by root.apache with the permissions 0640
