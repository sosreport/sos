# Copyright (C) 2013 Red Hat Inc., Harald Jensås <hjensas@redhat.com>

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

# hpasmcli.py
# Captures HP Server specific information during a sos run.

import sos.plugintools
import os

class hpasmcli(sos.plugintools.PluginBase):
    """HP Server hardware information
    """
    def checkenabled(self):
        if os.path.exists("/sbin/hpasmcli"):
            return True
        return False

    def setup(self):
        hpcmd = '/sbin/hpasmcli -s'
        cmdargs = [ '"SHOW ASR"', '"SHOW BOOT"', '"SHOW DIMM"',
                  '"SHOW DIMM SPD"', '"SHOW F1"', '"SHOW FANS"',
                  '"SHOW HT"', '"SHOW IML"', '"SHOW IPL"', '"SHOW NAME"',
                  '"SHOW PORTMAP"', '"SHOW POWERSUPPLY"', '"SHOW PXE"',
                  '"SHOW SERIAL BIOS"', '"SHOW SERIAL EMBEDDED" ',
                  '"SHOW SERIAL VIRTUAL"', '"SHOW SERVER"', '"SHOW TEMP"',
                  '"SHOW UID"', '"SHOW WOL"' ]
        for arg in cmdargs:
            cmd = hpcmd + ' ' + arg
            self.collectExtOutput(cmd, suggest_filename=arg)
        return
