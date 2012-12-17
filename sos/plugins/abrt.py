## Copyright (C) 2010 Red Hat, Inc., Tomas Smetana <tsmetana@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists

class abrt(Plugin, RedHatPlugin):
    """ABRT log dump
    """

    optionList = [("backtraces", 'collect backtraces for every report', 'slow', False)]

    def checkenabled(self):
        return self.isInstalled("abrt-cli") or \
               exists("/var/spool/abrt")

    def do_backtraces(self):
        ret, output, rtime = self.callExtProg('/usr/bin/sqlite3 /var/spool/abrt/abrt-db \'select UUID from abrt_v4\'')
        try:
            for uuid in output.split():
                self.addCmdOutput("/usr/bin/abrt-cli -ib %s" % uuid,
                    suggest_filename=("backtrace_%s" % uuid))
        except IndexError:
            pass

    def setup(self):
        self.addCmdOutput("/usr/bin/abrt-cli -lf",
                suggest_filename="abrt-log")
        if self.getOption('backtraces'):
            self.do_backtraces()
