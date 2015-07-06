# Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin


class Apport(Plugin, DebianPlugin, UbuntuPlugin):
    """Apport crash reporting tool
    """

    plugin_name = 'apport'
    profiles = ('debug',)

    def setup(self):
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
            self.add_copy_spec_limit("/var/log/apport.log",
                                     sizelimit=limit)
            self.add_copy_spec_limit("/var/log/apport.log.1",
                                     sizelimit=limit)
        else:
            self.add_copy_spec("/var/log/apport*")
        self.add_copy_spec("/etc/apport/*")
        self.add_copy_spec("/var/lib/whoopsie/whoopsie-id")
        self.add_cmd_output(
            "gdbus call -y -d com.ubuntu.WhoopsiePreferences \
            -o /com/ubuntu/WhoopsiePreferences \
            -m com.ubuntu.WhoopsiePreferences.GetIdentifier")
        self.add_cmd_output("ls -alh /var/crash/")
        self.add_cmd_output("bash -c 'grep -B 50 -m 1 ProcMaps /var/crash/*'")

# vim: set et ts=4 sw=4 :
