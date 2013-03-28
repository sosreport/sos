### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class veritas(Plugin, RedHatPlugin):
    """Veritas related information
    """
    # Information about VRTSexplorer obtained from
    # http://seer.entsupport.symantec.com/docs/243150.htm
    option_list = [("script", "Define VRTSexplorer script path", "", "/opt/VRTSspt/VRTSexplorer")]

    def check_enabled(self):
        return os.path.isfile(self.get_option("script"))

    def setup(self):
        """ interface with vrtsexplorer to capture veritas related data """
        stat, out, runtime = self.call_ext_prog(self.get_option("script"))
        try:
            for line in out.readlines():
                line = line.strip()
                tarfile = self.do_regex_find_all(r"ftp (.*tar.gz)", line)
            if len(tarfile) == 1:
                self.add_copy_spec(tarfile[0])
        except AttributeError, e:
            self.add_alert(e)
