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
import os

class openais(sos.plugintools.PluginBase):
    """openais related information
    """
    def checkenabled(self):
        if self.isInstalled("openais") or os.path.exists("/usr/sbin/openais-confdb-display"):
            ret, openais_ver, rtime = self.callExtProg("rpm -q --queryformat='%{VERSION}' openais")
            v, r, m = openais_ver.split('.')
            if int(r) >= 80 and int(m) >= 6:
                return True
        return False
        
    openais_config_opts = [('totem','token'), ('totem','consensus'),
                           ('totem','token_retransmits_before_loss_const'),
                           ('cman','quorum_dev_poll'), ('cman','expected_votes'),
                           ('cman','two_node')]
    
    def setup(self):
        self.collectExtOutput("openais-confdb-display")
        for item in self.openais_config_opts:
            obj, opt = item
            self.collectExtOutput("openais-confdb-display %s %s" % (obj, opt))
        return
