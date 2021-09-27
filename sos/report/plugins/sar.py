# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)
import re


class Sar(Plugin,):

    short_desc = 'System Activity Reporter'

    plugin_name = 'sar'
    profiles = ('system', 'performance')

    packages = ('sysstat',)
    sa_path = '/var/log/sa'
    option_list = [
        PluginOpt('all_sar', default=False,
                  desc="gather all system activity records")
    ]

    def setup(self):
        self.add_copy_spec(self.path_join(self.sa_path, '*'),
                           sizelimit=0 if self.get_option("all_sar") else None,
                           tailit=False)

        try:
            dir_list = self.listdir(self.sa_path)
        except OSError:
            self._log_warn("sar: could not list %s" % self.sa_path)
            return
        sa_regex = re.compile(r"sa[\d]+")
        # find all the sa files that don't have an existing sar file
        # there are two possible formats for sar files
        # saDD, the default one where DD is the day of the month
        # saYYYYMMDD, which is the format when specifying -D
        # as option for sadc
        for fname in dir_list:
            if sa_regex.match(fname):
                sa_data_path = self.path_join(self.sa_path, fname)
                sar_filename = 'sar' + fname[2:]
                if sar_filename not in dir_list:
                    sar_cmd = 'sh -c "sar -A -f %s"' % sa_data_path
                    self.add_cmd_output(sar_cmd, sar_filename)
                sadf_cmd = "sadf -x -- -A %s" % sa_data_path
                self.add_cmd_output(sadf_cmd, "%s.xml" % fname)


class RedHatSar(Sar, RedHatPlugin):

    sa_path = '/var/log/sa'


class DebianSar(Sar, DebianPlugin, UbuntuPlugin):

    sa_path = '/var/log/sysstat'

# vim: set et ts=4 sw=4 :
