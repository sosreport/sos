## hpasmcli.py
## Captures HP Server specific information during a sos run.

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

class hpasmcli(sos.plugintools.PluginBase):
    """HP Server related information
    """
    def checkenabled(self):
        if os.path.exists("/sbin/hpasmcli"):
            return True
        return False

    def setup(self):
        cmdargs = [ 'ASR', 'BOOT', 'DIMM', 'DIMM SPD', 'F1', 'FANS', 'HT', 'IML', 'IPL', 'NAME', 'PORTMAP', 'POWERSUPPLY', 'PXE', 'SERIAL BIOS', 'SERIAL EMBEDDED', 'SERIAL VIRTUAL', 'SERVER', 'TEMP', 'UID', 'WOL' ]
        for arg in cmdargs:
            cmd = '/sbin/hpasmcli -s "SHOW ' + arg + '"'
            self.collectExtOutput(cmd, suggest_filename=arg)
        return
