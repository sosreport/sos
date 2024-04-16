# Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>
# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt
from sos.utilities import is_executable


class Navicli(Plugin, RedHatPlugin):

    short_desc = 'EMC Navicli'

    plugin_name = 'navicli'
    profiles = ('storage', 'hardware')
    option_list = [
        PluginOpt('ipaddrs', default='', val_type=str,
                  desc='space-delimited list of CLARiiON IP addresses')
    ]

    def check_enabled(self):
        return is_executable("navicli")

    def get_navicli_config(self):
        """ EMC Navisphere Host Agent NAVICLI specific information - files
        """
        self.add_copy_spec([
            "/etc/Navisphere/agent.config",
            "/etc/Navisphere/Navimon.cfg",
            "/etc/Navisphere/Quietmode.cfg",
            "/etc/Navisphere/messages/[a-z]*",
            "/etc/Navisphere/log/[a-z]*"
        ])

    def get_navicli_sp_info(self, sp_address):
        """ EMC Navisphere Host Agent NAVICLI specific
        information - CLARiiON - commands
        """
        self.add_cmd_output([
            f"navicli -h {sp_address} getall",
            f"navicli -h {sp_address} getsptime -spa",
            f"navicli -h {sp_address} getsptime -spb",
            f"navicli -h {sp_address} getlog",
            f"navicli -h {sp_address} getdisk",
            f"navicli -h {sp_address} getcache",
            f"navicli -h {sp_address} getlun",
            f"navicli -h {sp_address} getlun -rg -type -default -owner -crus "
            "-capacity",
            f"navicli -h {sp_address} lunmapinfo",
            f"navicli -h {sp_address} getcrus",
            f"navicli -h {sp_address} port -list -all",
            f"navicli -h {sp_address} storagegroup -list",
            f"navicli -h {sp_address} spportspeed -get",
        ])

    def setup(self):
        self.get_navicli_config()
        for addr in set(self.get_option("ipaddrs").split()):
            if self.exec_cmd(f"navicli -h {addr} getsptime")['status'] == 0:
                self.get_navicli_sp_info(addr)

# vim: set et ts=4 sw=4 :
