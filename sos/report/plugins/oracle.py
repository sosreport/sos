# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class Oracle(Plugin, RedHatPlugin):
    short_desc = 'Oracle on Linux'

    plugin_name = "oracle"
    profiles = ('services',)
    packages = ('oracle',)

    pw_warn_text = " (password visible in process listings)"

    option_list = [
        PluginOpt('oratab', default='/etc/oratab', val_type=str,
                  desc='location of the oratab file')
    ]

    def setup(self):
        ora_tab = self.get_option('oratab')

        if os.path.isfile(ora_tab):
            self._log_warn("Found file oratab")
            try:
                with open(ora_tab, 'r', encoding='UTF-8') as ofile:
                    # Since the oratab file can have multiple unique SID
                    # entries that point to the same oracle home directory,
                    # keep track of the unique paths so we don't gather
                    # duplicate files
                    path_list = []
                    for line in ofile.read().splitlines():
                        if not line.startswith('#') and \
                           not line.isspace() and \
                           len(line) != 0:
                            words = line.split(':')
                            # check if this path has already been collected
                            if not words[1] in path_list:
                                path_list.append(words[1])
                                oracle_path = words[1]
                                if not oracle_path.endswith('/'):
                                    oracle_path = f"{oracle_path}/"
                                self.add_copy_spec([
                                    f"{oracle_path}dbs/init*.ora",
                                    f"{oracle_path}dbs/spfile*.ora"
                                ])

            except IOError as ex:
                self._log_error(f'Could not open conf file {ora_tab}: {ex}')
                return
        else:
            self._log_warn("Could not locate oratab file. "
                           "Oracle data will not be collected.")

# vim: set et ts=4 sw=4 :
