# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from datetime import datetime as dt
import os
import re
from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)


class Sar(Plugin):
    """
    The sar plugin is designed to collect system performance data as recorded
    by sysstat.

    The raw binary data, i.e. the 'saX' files, will be collected and for files
    a week old or younger, this plugin will capture human-readable conversions
    of those files provided by the 'sar' command locally available, if the
    local sysstat installation has not already created a converted copy (e.g.
    for the current day-of data being collected at the time of report
    generation).

    Using the 'all-sar' plugin option will not only cause the plugin to capture
    _all_ 'saX' files present on the host, but further perform the 'sar'
    conversion on all files, not just those produced within the last week.

    Converted 'sar' files will be written to the sos_commands/sar/, and not
    to the /var/log/ path that sysstat writes to.

    Note that this conversion is done because it is unlikely that the same
    version of sysstat that produces the 'saX' files will be the same version
    available on a given analyst's workstation, and this conversion is version
    sensitive.
    """

    short_desc = 'System Activity Reporter'

    plugin_name = 'sar'
    profiles = ('system', 'performance')

    packages = ('sysstat',)
    sa_path = '/var/log/sa'
    option_list = [
        PluginOpt('all-sar', default=False,
                  desc="gather all system activity records")
    ]

    def setup(self):
        self.add_copy_spec(self.path_join(self.sa_path, '*'),
                           sizelimit=0 if self.get_option("all-sar") else None,
                           tailit=False)

        try:
            dir_list = self.listdir(self.sa_path)
        except OSError:
            self._log_warn(f"sar: could not list {self.sa_path}")
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
                    # only collect sar output for the last 7 days by default
                    if not self.get_option('all-sar') and \
                       self.is_older_than_7days(sa_data_path):
                        continue
                    sar_cmd = f"sar -A -f {sa_data_path}"
                    self.add_cmd_output(sar_cmd, sar_filename)
                sadf_cmd = f"sadf -x -- -A {sa_data_path}"
                self.add_cmd_output(sadf_cmd, f"{fname}.xml")

    def is_older_than_7days(self, sarfile):
        """ Is the file older than 7 days? """
        try:
            _ftime = os.stat(sarfile).st_mtime
            _age = dt.today() - dt.fromtimestamp(_ftime)
            if _age.days <= 7:
                return False
        except Exception as err:  # pylint: disable=broad-except
            self._log_warn(f"Could not determine age of '{sarfile}' - "
                           f"skipping converting to sar format: {err}")

        return True


class RedHatSar(Sar, RedHatPlugin):

    sa_path = '/var/log/sa'


class DebianSar(Sar, DebianPlugin, UbuntuPlugin):

    sa_path = '/var/log/sysstat'

# vim: set et ts=4 sw=4 :
