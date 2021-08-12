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

    def get_navicli_SP_info(self, SP_address):
        """ EMC Navisphere Host Agent NAVICLI specific
        information - CLARiiON - commands
        """
        self.add_cmd_output([
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

    def setup(self):
        self.get_navicli_config()
        for ip in set(self.get_option("ipaddrs").split()):
            if self.exec_cmd("navicli -h %s getsptime" % (ip))['status'] == 0:
                self.get_navicli_SP_info(ip)

# vim: set et ts=4 sw=4 :
