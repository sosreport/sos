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

class sar(sos.plugintools.PluginBase):
    """Generate the sar file from /var/log/sa/saXX files
    """

    packages = ('sysstat',)
    sa_path = "/var/log/sa"
    optionList = [("all_sar", "gather all system activity records", "", False)]

    # size-limit SAR data collected by default (MB)
    sa_size = 20

    def setup(self):
        if self.getOption("all_sar"):
            self.sa_size = 0

        # Copy all sa??, sar??, sa??.* and sar??.* files, which will net
        # compressed and uncompressed versions, typically.
        for suffix in ('', '.*'):
            self.addCopySpecLimit(
                os.path.join(self.sa_path, "sa[0-3][0-9]" + suffix),
                sizelimit=self.sa_size, tailit=False
            )
            self.addCopySpecLimit(
                os.path.join(self.sa_path, "sar[0-3][0-9]" + suffix),
                sizelimit=self.sa_size, tailit=False
            )
            
        try:
            dirList=os.listdir(self.sa_path)
        except:
            self.soslog.error("sar: could not list %s" % self.sa_path)
            return
        # find all the sa file that don't have an existing sar file
        for fname in dirList:
            if fname.startswith('sar'):
                continue
            if not fname.startswith('sa'):
                continue
            if len(fname) != 4:
                # We either have an "sa" or "sa?" file, or more likely, a
                # compressed data file like, "sa??.xz".
                #
                # FIXME: We don't have a detector for the kind of compression
                # use for this file right now, so skip these kinds of files.
                continue
            sa_data_path = os.path.join(self.sa_path, fname)
            sar_filename = 'sar' + fname[2:]
            if sar_filename not in dirList:
                sar_cmd = 'sh -c "sar -A -f %s"' % sa_data_path
                self.collectExtOutput(sar_cmd, sar_filename)
            sadf_cmd = "sadf -x %s" % sa_data_path
            self.collectExtOutput(sadf_cmd, "%s.xml" % fname)


    def checkenabled(self):
        if os.path.exists("/var/log/sa") and os.path.exists("/usr/bin/sar"):
            return True
        return False    

