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

class printing(sos.plugintools.PluginBase):
    """printing related information (cups)
    """
    optionList = [("logsize", "max size (MiB) to collect per log file", "", 5),
                  ("all_logs", "collect all cups log files", "", False)]

    def setup(self):
        # all_logs takes precedence over logsize
        if not self.getOption("all_logs"):
            limit = self.getOption("logsize")
            self.addCopySpecLimit("/var/log/cups/access_log", sizelimit=limit)
            self.addCopySpecLimit("/var/log/cups/error_log", sizelimit=limit)
            self.addCopySpecLimit("/var/log/cups/page_log", sizelimit=limit)
        else:
            self.addCopySpec("/var/log/cups")
        self.addCopySpec("/etc/cups/*.conf")
        self.addCopySpec("/etc/cups/lpoptions")
        self.addCopySpec("/etc/cups/ppd/*.ppd")
        self.collectExtOutput("/usr/bin/lpstat -t")
        self.collectExtOutput("/usr/bin/lpstat -s")
        self.collectExtOutput("/usr/bin/lpstat -d")

        return

