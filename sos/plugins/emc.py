## emc.py
## Captures EMC specific information during a sos run.

## Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sos.plugintools, os 

class emc(sos.plugintools.PluginBase):
    """EMC related information (PowerPath, Solutions Enabler CLI and Navisphere CLI)
    """

    def about_emc(self):
        """ EMC Corporation specific information
        """
        self.addCustomText('<center><h1><font size="+4"color="blue">EMC&sup2;</font><font size="-2" color="blue">&reg;</font>')
        self.addCustomText('<br><font size="+1">where information lives</font><font size="-2">&reg;</font></h1>')
        self.addCustomText("EMC Corporation is the world's leading developer and provider of information ")
        self.addCustomText("infrastructure technology and solutions that enable organizations of all sizes to transform ")
        self.addCustomText("the way they compete and create value from their information. &nbsp;")
        self.addCustomText("Information about EMC's products and services can be found at ")
        self.addCustomText('<a href="http://www.EMC.com/">www.EMC.com</a>.</center>')
        return

    def get_pp_files(self):
        """ EMC PowerPath specific information - files
        """
        self.collectExtOutput("/sbin/powermt version")
        self.addCopySpec("/etc/init.d/PowerPath")
        self.addCopySpec("/etc/powermt.custom")
        self.addCopySpec("/etc/emcp_registration")
        self.addCopySpec("/etc/emc/mpaa.excluded")
        self.addCopySpec("/etc/emc/mpaa.lams")
        self.addCopySpec("/etc/emcp_devicesDB.dat")
        self.addCopySpec("/etc/emcp_devicesDB.idx")
        self.addCopySpec("/etc/emc/powerkmd.custom")
        self.addCopySpec("/etc/modprobe.conf.pp")
        return

    def get_pp_config(self):
        """ EMC PowerPath specific information - commands
        """
        self.collectExtOutput("/sbin/powermt display")
        self.collectExtOutput("/sbin/powermt display dev=all")
        self.collectExtOutput("/sbin/powermt check_registration")
        self.collectExtOutput("/sbin/powermt display options")
        self.collectExtOutput("/sbin/powermt display ports")
        self.collectExtOutput("/sbin/powermt display paths")
        self.collectExtOutput("/sbin/powermt dump")
        return

    def get_symcli_files(self):
        """ EMC Solutions Enabler SYMCLI specific information - files
        """
        self.addCopySpec("/var/symapi/db/symapi_db.bin")
        self.addCopySpec("/var/symapi/config/[a-z]*")
        self.addCopySpec("/var/symapi/log/[a-z]*")
        return

    def get_symcli_config(self):
        """ EMC Solutions Enabler SYMCLI specific information - Symmetrix/DMX - commands
        """
        self.collectExtOutput("/usr/symcli/bin/symcli -def")
        self.collectExtOutput("/usr/symcli/bin/symdg list")
        self.collectExtOutput("/usr/symcli/bin/symdg -v list")
        self.collectExtOutput("/usr/symcli/bin/symcg list")
        self.collectExtOutput("/usr/symcli/bin/symcg -v list")
        self.collectExtOutput("/usr/symcli/bin/symcfg list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -v list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -db")
        self.collectExtOutput("/usr/symcli/bin/symcfg -semaphores list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -dir all -v list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -connections list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -app -v list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -fa all -port list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -ra all -port list")
        self.collectExtOutput("/usr/symcli/bin/symcfg -sa all -port list")
        self.collectExtOutput("/usr/symcli/bin/symcfg list -lock")
        self.collectExtOutput("/usr/symcli/bin/symcfg list -lockn all")
        self.collectExtOutput("/usr/symcli/bin/syminq")
        self.collectExtOutput("/usr/symcli/bin/syminq -v")
        self.collectExtOutput("/usr/symcli/bin/syminq -symmids")
        self.collectExtOutput("/usr/symcli/bin/syminq hba -fibre")
        self.collectExtOutput("/usr/symcli/bin/syminq hba -scsi")
        self.collectExtOutput("/usr/symcli/bin/symhost show -config")
        self.collectExtOutput("/usr/symcli/bin/stordaemon list")
        self.collectExtOutput("/usr/symcli/bin/stordaemon -v list")
        self.collectExtOutput("/usr/symcli/bin/sympd list")
        self.collectExtOutput("/usr/symcli/bin/sympd list -vcm")
        self.collectExtOutput("/usr/symcli/bin/symdev list")
        self.collectExtOutput("/usr/symcli/bin/symdev -v list")
        self.collectExtOutput("/usr/symcli/bin/symdev -rdfa list")
        self.collectExtOutput("/usr/symcli/bin/symdev -rdfa -v list")
        self.collectExtOutput("/usr/symcli/bin/symbcv list")
        self.collectExtOutput("/usr/symcli/bin/symbcv -v list")
        self.collectExtOutput("/usr/symcli/bin/symrdf list")
        self.collectExtOutput("/usr/symcli/bin/symrdf -v list")
        self.collectExtOutput("/usr/symcli/bin/symrdf -rdfa list")
        self.collectExtOutput("/usr/symcli/bin/symrdf -rdfa -v list")
        self.collectExtOutput("/usr/symcli/bin/symsnap list")
        self.collectExtOutput("/usr/symcli/bin/symsnap list -savedevs")
        self.collectExtOutput("/usr/symcli/bin/symclone list")
        self.collectExtOutput("/usr/symcli/bin/symevent list")
        self.collectExtOutput("/usr/symcli/bin/symmask list hba")
        self.collectExtOutput("/usr/symcli/bin/symmask list logins")
        self.collectExtOutput("/usr/symcli/bin/symmaskdb list database")
        self.collectExtOutput("/usr/symcli/bin/symmaskdb -v list database")
        return

    def get_navicli_config(self):
        """ EMC Navisphere Host Agent NAVICLI specific information - files
        """
        self.addCopySpec("/etc/Navisphere/agent.config")
        self.addCopySpec("/etc/Navisphere/Navimon.cfg")
        self.addCopySpec("/etc/Navisphere/Quietmode.cfg")
        self.addCopySpec("/etc/Navisphere/messages/[a-z]*")
        self.addCopySpec("/etc/Navisphere/log/[a-z]*")
        return

    def get_navicli_SP_info(self,SP_address):
        """ EMC Navisphere Host Agent NAVICLI specific information - CLARiiON - commands
        """
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getall" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getsptime -spa" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getsptime -spb" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getlog" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getdisk" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getcache" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getlun" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getlun -rg -type -default -owner -crus -capacity" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s lunmapinfo" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s getcrus" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s port -list -all" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s storagegroup -list" % SP_address)
        self.collectExtOutput("/opt/Navisphere/bin/navicli -h %s spportspeed -get" % SP_address)
        return

    def checkenabled(self):
        self.packages = [ "EMCpower" ]
        self.files = [ "/opt/Navisphere/bin", "/proc/emcp" ]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        from subprocess import Popen, PIPE
        ## About EMC Corporation default no if no EMC products are installed
        add_about_emc="no"

        ## If PowerPath is installed collect PowerPath specific information
        emc_pp_installed = Popen("/bin/rpm -qa | /bin/grep -i EMCpower", shell=True, stdout=PIPE).stdout.read()
        if emc_pp_installed != "":
            print "EMC PowerPath is installed."
            print " Gathering EMC PowerPath information..."
            self.addCustomText("EMC PowerPath is installed.<br>")
            self.get_pp_files()
            add_about_emc = "yes"

        ## If PowerPath is running collect additional PowerPath specific information
        if os.path.isdir("/proc/emcp"):
            print "EMC PowerPath is running."
            print " Gathering additional EMC PowerPath information..."
            self.get_pp_config()

        ## If Solutions Enabler is installed collect Symmetrix/DMX specific information
        emc_symcli_installed = Popen("/bin/rpm -qa | /bin/grep -i symcli-symcli", shell=True, stdout=PIPE).stdout.read()
        if emc_symcli_installed != "":
            print "EMC Solutions Enabler SYMCLI is installed."
            print " Gathering EMC Solutions Enabler SYMCLI information..."
            self.addCustomText("EMC Solutions Enabler is installed.<br>")
            self.get_symcli_files()
            self.get_symcli_config()
            add_about_emc = "yes"

        ## If Navisphere Host Agent is installed collect CLARiiON specific information
        if os.path.isdir("/opt/Navisphere/bin"):
            print ""
            print "The EMC CLARiiON Navisphere Host Agent is installed."
            self.addCustomText("EMC CLARiiON Navisphere Host Agent is installed.<br>")
            self.get_navicli_config()
            print " Gathering Navisphere NAVICLI Host Agent information..."
            print " Please enter a CLARiiON SP IP address.  In order to collect"
            print " information for both SPA and SPB as well as multiple"
            print " CLARiiON arrays (if desired) you will be prompted multiple times."
            print " To exit simply press [Enter]"
            print ""
            add_about_emc = "yes"
            CLARiiON_IP_address_list = []
            CLARiiON_IP_loop = "stay_in"
            while CLARiiON_IP_loop == "stay_in":
                ans = raw_input("CLARiiON SP IP Address or [Enter] to exit: ")
                ## Check to make sure the CLARiiON SP IP address provided is valid
                p = Popen("/opt/Navisphere/bin/navicli -h %s getsptime" % (ans,), shell=True, stdout=PIPE, stderr=PIPE)
                out, err = p.communicate()
                if p.returncode == 0:
                    CLARiiON_IP_address_list.append(ans)
                else:
                    if ans != "":
                        print "The IP address you entered, %s, is not to an active CLARiiON SP." % ans
                    if ans == "":
                        CLARiiON_IP_loop = "get_out"
            ## Sort and dedup the list of CLARiiON IP Addresses
            CLARiiON_IP_address_list.sort()
            for SP_address in CLARiiON_IP_address_list:
                if CLARiiON_IP_address_list.count(SP_address) > 1:
                    CLARiiON_IP_address_list.remove(SP_address)
            for SP_address in CLARiiON_IP_address_list:
                if SP_address != "":
                    print " Gathering NAVICLI information for %s..." % SP_address
                    self.get_navicli_SP_info(SP_address)

        ## Only provide About EMC if EMC products are installed
        if add_about_emc != "no":
            self.about_emc()
        return
