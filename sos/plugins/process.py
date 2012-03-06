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
import time
import os

class process(sos.plugintools.PluginBase):
    """process information
    """
    def setup(self):
        self.collectExtOutput("/bin/ps auxwww", symlink = "ps")
        self.collectExtOutput("/bin/ps auxwwwm")
        self.collectExtOutput("/bin/ps alxwww")
        self.collectExtOutput("/usr/bin/pstree", symlink = "pstree")
        self.collectExtOutput("/usr/sbin/lsof -b +M -n -l", symlink = "lsof")
        return

    def find_mountpoint(s):
        if (os.path.ismount(s) or len(s)==0): return s
        else: return mountpoint(os.path.split(s)[0])

    def diagnose(self):
        from subprocess import Popen, PIPE
        # check that no process is in state D
        dpids = []
        p = Popen("/bin/ps -A -o state,pid --no-heading", shell=True, stdout=PIPE, stderr=PIPE, bufsize=-1)
        out, err = p.communicate()
        if not p.returncode:
            for line in out.split("\n")[:-1]:
                line = line.split()
                if line[0] == "D":
                    # keep an eye on the process to see if the stat changes
                    for inc in range(1,10):
                        try:
                            if len(self.fileGrep("^State: D", " /proc/%d/status" % int(line[1]))) == 0:
                                # status is not D, good. let's get out of the loop.
                                time.sleep(0.1 * inc)
                                continue
                        except IOError:
                            # this should never happen...
                            pass
                    else:
                        # still D after 0.1 * range(1,5) seconds
                        dpids.append(int(line[1]))

        if len(dpids):
            self.addDiagnose("one or more processes are in state D (sosreport might hang)")

        return



