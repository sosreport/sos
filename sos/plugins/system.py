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

class system(Plugin, RedHatPlugin):
    """core system related information
    """
    def setup(self):
        self.addCopySpecs([
            "/proc/sys",
            "/etc/cron*",
            "/etc/anacrontab",
            "/var/spool/cron*",
            "/var/log/cron*",
            "/etc/syslog.conf",
            "/etc/rsyslog.conf",
            "/etc/ntp.conf",
            "/etc/ntp/step-tickers",
            "/etc/ntp/ntpservers"])
        self.addForbiddenPath(
                "/proc/sys/net/ipv8/neigh/*/retrans_time")
        self.addForbiddenPath(
                "/proc/sys/net/ipv6/neigh/*/base_reachable_time")

        self.collectExtOutput("/usr/bin/crontab -l")
        
