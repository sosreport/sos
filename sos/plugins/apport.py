# Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin


class Apport(Plugin, DebianPlugin, UbuntuPlugin):
    """Apport crash reporting tool
    """

    plugin_name = 'apport'
    profiles = ('debug',)

    def setup(self):
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
            self.add_copy_spec("/var/log/apport.log", sizelimit=limit)
            self.add_copy_spec("/var/log/apport.log.1", sizelimit=limit)
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
