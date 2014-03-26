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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Sar(Plugin,):
    """ Collect system activity reporter data
    """

    plugin_name = 'sar'

    packages = ('sysstat',)
    sa_path = '/var/log/sa'
    option_list = [("all_sar", "gather all system activity records", "", False)]

    # size-limit SAR data collected by default (MB)
    sa_size = 20

    def setup(self):
        if self.get_option("all_sar"):
            self.sa_size = 0

        self.add_copy_spec_limit("%s/sar[0-9]*" % self.sa_path,
                                 sizelimit = self.sa_size)
        self.add_copy_spec_limit("%s/sa[0-9]*" % self.sa_path,
                              sizelimit = self.sa_size)
        try:
            dirList = os.listdir(self.sa_path)
        except:
            self.soslog.warning("sar: could not list %s" % self.sa_path)
            return
        # find all the sa file that don't have an existing sar file
        for fname in dirList:
            if fname[0:2] == 'sa' and fname[2] != 'r':
                sar_filename = 'sar' + fname[2:4]
                sa_data_path = os.path.join(self.sa_path, fname)
                if sar_filename not in dirList:
                    sar_cmd = 'sh -c "LANG=C sar -A -f %s"' % sa_data_path
                    self.add_cmd_output(sar_cmd, sar_filename)
                sadf_cmd = "sadf -x %s" % sa_data_path
                self.add_cmd_output(sadf_cmd, "%s.xml" % fname)
        self.add_copy_spec(os.path.join(self.sa_path, "sar*"))


class RedHatSar(Sar, RedHatPlugin):
    """ Collect system activity reporter data
    """

    sa_path = '/var/log/sa'


class DebianSar(Sar, DebianPlugin, UbuntuPlugin):
    """ Collect system activity reporter data
    """
    
    sa_path = '/var/log/sysstat'

# vim: et ts=4 sw=4
