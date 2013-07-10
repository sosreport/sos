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

# hpacucli.py
# Captures HP Smart Array specific information during a sos run
# if HP Array Configuration Utility CLI, hpacucli, for Linux is 
# available.
#
# The following is caputered:
#   - List of all HP Smart Array and RAID controllers
#   - Status of all HP Smart Array and RAID controllers
#   - Detauls of all HP Smart Array and RAID controllers
#   - Diagnostics information from all HP Smart Array and RAID controllers
#
# HP Array Configuration Utility CLI for Linux
#
# The Array Configuration Utility CLI is a commandline-based disk 
# configuration program for Smart Array Controllers and RAID Array 
# Controllers. 

import sos.plugintools
import os
import tempfile
import shutil
import zipfile

def unzip(zipfilepath, dstdir):
    zf = zipfile.ZipFile(zipfilepath)
    for name in zf.namelist():
        (dirname, filename) = os.path.split(name)
        if filename == '':
            newdir = os.path.join(dstdir, dirname)
            if not os.path.exists(newdir):
                os.mkdir(newdir)
        else:
            fd = open(os.path.join(dstdir, name), 'wb')
            fd.write(zf.read(name))
            fd.close()
    zf.close()

class hpacucli(sos.plugintools.PluginBase):
    """HP Smart Array RAID Storage information
    """
    def checkenabled(self):
        if os.path.exists("/usr/sbin/hpacucli"):
            return True
        return False

    def setup(self):
        # Capture ctrl show commands output
        self.collectExtOutput("/usr/sbin/hpacucli ctrl all show")
        self.collectExtOutput("/usr/sbin/hpacucli ctrl all show status")
        self.collectExtOutput("/usr/sbin/hpacucli ctrl all show detail")
        # hpacuclu insist on creating a zip archive for diag
        tmpdir = tempfile.mkdtemp()
        filename = "hpacucli-diag.zip"
        filepath = os.path.join(tmpdir, filename)
        self.callExtProg("/usr/sbin/hpacucli ctrl all diag file=" + filepath)
        # Extract diag content into cmddir
        diagdir = os.path.join(self.cInfo['cmddir'], "hpacucli/diag")
        if not os.path.exists(diagdir):
            os.makedirs(diagdir)
        unzip(filepath, diagdir)
        shutil.rmtree(tmpdir)
        return
