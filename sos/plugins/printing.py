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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class printing(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """printing related information (cups)
    """
    optionList = [("cups", "max size (MiB) to collect per cups log file",
                   "", 50)]

    def setup(self):
        self.add_copy_specs([
            "/etc/cups/*.conf",
            "/etc/cups/lpoptions",
            "/etc/cups/ppd/*.ppd"])
        self.add_copy_spec_limit("/var/log/cups", sizelimit=self.option_enabled("cupslogsize"))
        self.add_cmd_output("/usr/bin/lpstat -t")
        self.add_cmd_output("/usr/bin/lpstat -s")
        self.add_cmd_output("/usr/bin/lpstat -d")
