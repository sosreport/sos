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
import os, glob

class Sar(Plugin,):
    """ Collect system activity reporter data
    """

    plugin_name = 'sar'

    packages = ('sysstat',)
    sa_path = '/var/log/sa'
    option_list = [("all_sar", "gather all system activity records", "", False),
                   ("data_file_limit", "limit the number of binary sa?? data files collected to the N most recent", "", 0),
                   ("skip_sar_reports", "don't gather sar?? generated reports", "", False)]

    # size-limit SAR data collected by default (MB)
    sa_size = 20

    def check_enabled(self):
        # check to see if we are force-enabled with no sar installation
        if not os.path.exists(self.sa_path) or not os.path.isdir(self.sa_path):
            self.soslog.info("sar directory %s does not exist" % self.sa_path
                            + " or is not a directory")
            return False
        return True

    def setup(self):
        if self.get_option("all_sar"):
            self.sa_size = 0

        glob_path = os.path.join(self.sa_path, "sa[0-9]*")
        limit = self.get_option("data_file_limit")
        if limit > 0:
            # Get the most recent N binary datafiles
            files = sorted(glob.glob(glob_path), key=os.path.getmtime)
            self.add_copy_specs(files[:limit])
        else:
            self.add_copy_spec_limit(glob_path, sizelimit = self.sa_size)

        if self.get_option("skip_sar_reports"):
            return

        self.add_copy_spec_limit(os.path.join(self.sa_path, "sar[0-9]*"),
                                              sizelimit = self.sa_size)
        try:
            dirList = os.listdir(self.sa_path)
        except:
            self.soslog.warning("sar: could not list %s", self.sa_path)
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
