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
    """ EMC related information (PowerPath, Solutions Enabler
    CLI and Navisphere CLI)
    """

    plugin_name = 'emc'

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

    def get_symcli_files(self):
        """ EMC Solutions Enabler SYMCLI specific information - files
        """
        self.add_copy_specs([
            "/var/symapi/db/symapi_db.bin",
            "/var/symapi/config/[a-z]*",
            "/var/symapi/log/[a-z]*"
        ])

    def get_symcli_config(self):
        """ EMC Solutions Enabler SYMCLI specific information
        - Symmetrix/DMX - commands
        """
        self.add_cmd_outputs([
            "symclisymcli -def",
            "symclisymdg list",
            "symclisymdg -v list",
            "symclisymcg list",
            "symclisymcg -v list",
            "symclisymcfg list",
            "symclisymcfg -v list",
            "symclisymcfg -db",
            "symclisymcfg -semaphores list",
            "symclisymcfg -dir all -v list",
            "symclisymcfg -connections list",
            "symclisymcfg -app -v list",
            "symclisymcfg -fa all -port list",
            "symclisymcfg -ra all -port list",
            "symclisymcfg -sa all -port list",
            "symclisymcfg list -lock",
            "symclisymcfg list -lockn all",
            "symclisyminq",
            "symclisyminq -v",
            "symclisyminq -symmids",
            "symclisyminq hba -fibre",
            "symclisyminq hba -scsi",
            "symclisymhost show -config",
            "symclistordaemon list",
            "symclistordaemon -v list",
            "symclisympd list",
            "symclisympd list -vcm",
            "symclisymdev list",
            "symclisymdev -v list",
            "symclisymdev -rdfa list",
            "symclisymdev -rdfa -v list",
            "symclisymbcv list",
            "symclisymbcv -v list",
            "symclisymrdf list",
            "symclisymrdf -v list",
            "symclisymrdf -rdfa list",
            "symclisymrdf -rdfa -v list",
            "symclisymsnap list",
            "symclisymsnap list -savedevs",
            "symclisymclone list",
            "symclisymevent list",
            "symclisymmask list hba",
            "symclisymmask list logins",
            "symclisymmaskdb list database",
            "symclisymmaskdb -v list database"
        ])

    def get_navicli_config(self):
        """ EMC Navisphere Host Agent NAVICLI specific information - files
        """
        self.add_copy_specs([
            "/etc/Navisphere/agent.config",
            "/etc/Navisphere/Navimon.cfg",
            "/etc/Navisphere/Quietmode.cfg",
            "/etc/Navisphere/messages/[a-z]*",
            "/etc/Navisphere/log/[a-z]*"
        ])

    def get_navicli_SP_info(self, SP_address):
        """ EMC Navisphere Host Agent NAVICLI specific
        information - CLARiiON - commands
        """
        self.add_cmd_outputs([
            "navicli -h %s getall" % SP_address,
            "navicli -h %s getsptime -spa" % SP_address,
            "navicli -h %s getsptime -spb" % SP_address,
            "navicli -h %s getlog" % SP_address,
            "navicli -h %s getdisk" % SP_address,
            "navicli -h %s getcache" % SP_address,
            "navicli -h %s getlun" % SP_address,
            "navicli -h %s getlun -rg -type -default -owner -crus "
            "-capacity" % SP_address,
            "navicli -h %s lunmapinfo" % SP_address,
            "navicli -h %s getcrus" % SP_address,
            "navicli -h %s port -list -all" % SP_address,
            "navicli -h %s storagegroup -list" % SP_address,
            "navicli -h %s spportspeed -get" % SP_address
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

        # If Solutions Enabler is installed collect Symmetrix/DMX specific
        # information
        if len(self.policy().package_manager.all_pkgs_by_name_regex(
                '[Ss][Yy][Mm][Cc][Ll][Ii]-[Ss][Yy][Mm][Cc][Ll][Ii]')) > 0:
            print("EMC Solutions Enabler SYMCLI is installed.")
            print(" Gathering EMC Solutions Enabler SYMCLI information...")
            self.add_custom_text("EMC Solutions Enabler is installed.<br>")
            self.get_symcli_files()
            self.get_symcli_config()
            add_about_emc = "yes"

        # If Navisphere Host Agent is installed collect CLARiiON specific
        # information
        if os.path.isdir("/opt/Navisphere/bin"):
            print("")
            print("The EMC CLARiiON Navisphere Host Agent is installed.")
            self.add_custom_text("EMC CLARiiON Navisphere Host Agent is "
                                 "installed.<br>")
            self.get_navicli_config()
            print(" Gathering Navisphere NAVICLI Host Agent information...")
            print(" Please enter a CLARiiON SP IP address.  In order to "
                  "collect")
            print(" information for both SPA and SPB as well as multiple")
            print(" CLARiiON arrays (if desired) you will be prompted "
                  "multiple times.")
            print(" To exit simply press [Enter]")
            print("")
            add_about_emc = "yes"
            CLARiiON_IP_address_list = []
            CLARiiON_IP_loop = "stay_in"
            while CLARiiON_IP_loop == "stay_in":
                ans = input("CLARiiON SP IP Address or [Enter] to exit: ")
                # Check to make sure the CLARiiON SP IP address provided is
                # valid
                p = Popen("navicli -h %s getsptime" % (ans,),
                          shell=True, stdout=PIPE, stderr=PIPE,
                          close_fds=True)
                out, err = p.communicate()
                if p.returncode == 0:
                    CLARiiON_IP_address_list.append(ans)
                else:
                    if ans != "":
                        print("The IP address you entered, %s, is not to an "
                              "active CLARiiON SP." % ans)
                    if ans == "":
                        CLARiiON_IP_loop = "get_out"
            # Sort and dedup the list of CLARiiON IP Addresses
            CLARiiON_IP_address_list.sort()
            for SP_address in CLARiiON_IP_address_list:
                if CLARiiON_IP_address_list.count(SP_address) > 1:
                    CLARiiON_IP_address_list.remove(SP_address)
            for SP_address in CLARiiON_IP_address_list:
                if SP_address != "":
                    print(" Gathering NAVICLI information for %s..." %
                          SP_address)
                    self.get_navicli_SP_info(SP_address)

        # Only provide About EMC if EMC products are installed
        if add_about_emc != "no":
            self.about_emc()

# vim: et ts=4 sw=4
