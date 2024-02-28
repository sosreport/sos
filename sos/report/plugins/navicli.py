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
            "navicli -h %s getall" % sp_address,
            "navicli -h %s getsptime -spa" % sp_address,
            "navicli -h %s getsptime -spb" % sp_address,
            "navicli -h %s getlog" % sp_address,
            "navicli -h %s getdisk" % sp_address,
            "navicli -h %s getcache" % sp_address,
            "navicli -h %s getlun" % sp_address,
            "navicli -h %s getlun -rg -type -default -owner -crus "
            "-capacity" % sp_address,
            "navicli -h %s lunmapinfo" % sp_address,
            "navicli -h %s getcrus" % sp_address,
            "navicli -h %s port -list -all" % sp_address,
            "navicli -h %s storagegroup -list" % sp_address,
            "navicli -h %s spportspeed -get" % sp_address
        ])

    def setup(self):
        self.get_navicli_config()
        for addr in set(self.get_option("ipaddrs").split()):
            if self.exec_cmd(f"navicli -h {addr} getsptime")['status'] == 0:
                self.get_navicli_sp_info(addr)

# vim: set et ts=4 sw=4 :
