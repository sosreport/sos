# Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

""" Captures EMC specific information during a sos run. """

from sos.plugins import Plugin, RedHatPlugin, os

# Just for completeness sake.
from six.moves import input


class Emc(Plugin, RedHatPlugin):
    """ EMC related information
    """

    plugin_name = 'emc'
    profiles = ('storage', 'hardware')

    def about_emc(self):
        """ EMC Corporation specific information
        """
        self.add_custom_text(
            '<center><h1><font size="+4"color="blue">'
            'EMC&sup2;</font><font size="-2" color="blue">&reg;</font>')
        self.add_custom_text(
            '<br><font size="+1">where information lives</font>'
            '<font size="-2">&reg;</font></h1>')
        self.add_custom_text(
            "EMC Corporation is the world's leading developer and provider "
            "of information ")
        self.add_custom_text(
            "infrastructure technology and solutions that "
            "enable organizations of all sizes to transform ")
        self.add_custom_text(
            "the way they compete and create value from their "
            "information. &nbsp;")
        self.add_custom_text(
            "Information about EMC's products and services "
            "can be found at ")
        self.add_custom_text(
            '<a href="http://www.EMC.com/">www.EMC.com</a>.</center>')

    def get_pp_files(self):
        """ EMC PowerPath specific information - files
        """
        self.add_cmd_output("powermt version")
        self.add_copy_specs([
            "/etc/init.d/PowerPath",
            "/etc/powermt.custom",
            "/etc/emcp_registration",
            "/etc/emc/mpaa.excluded",
            "/etc/emc/mpaa.lams",
            "/etc/emcp_devicesDB.dat",
            "/etc/emcp_devicesDB.idx",
            "/etc/emc/powerkmd.custom",
            "/etc/modprobe.conf.pp"
        ])

    def get_pp_config(self):
        """ EMC PowerPath specific information - commands
        """
        self.add_cmd_outputs([
            "powermt display",
            "powermt display dev=all",
            "powermt check_registration",
            "powermt display options",
            "powermt display ports",
            "powermt display paths",
            "powermt dump"
        ])

    def check_enabled(self):
        self.packages = ["EMCpower"]
        self.files = ["/opt/Navisphere/bin", "/proc/emcp"]
        return Plugin.check_enabled(self)

    def setup(self):
        from subprocess import Popen, PIPE
        # About EMC Corporation default no if no EMC products are installed
        add_about_emc = "no"

        # If PowerPath is installed collect PowerPath specific information
        if self.is_installed("EMCpower"):
            print("EMC PowerPath is installed.")
            print(" Gathering EMC PowerPath information...")
            self.add_custom_text("EMC PowerPath is installed.<br>")
            self.get_pp_files()
            add_about_emc = "yes"

        # If PowerPath is running collect additional PowerPath specific
        # information
        if os.path.isdir("/proc/emcp"):
            print("EMC PowerPath is running.")
            print(" Gathering additional EMC PowerPath information...")
            self.get_pp_config()

        # Only provide About EMC if EMC products are installed
        if add_about_emc != "no":
            self.about_emc()

# vim: et ts=4 sw=4
