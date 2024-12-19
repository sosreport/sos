# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class Oratab(Plugin, RedHatPlugin):
    short_desc = 'Oratab discovery for Oracle instances on Linux'

    plugin_name = "oratab"
    profiles = ('services',)
    packages = ('oratab',)

    option_list = [
        PluginOpt('oratab', default='/etc/oratab', val_type=str,
                  desc='location of the oratab file')
    ]

    def setup(self):
        ora_tab = self.get_option('oratab')

        if os.path.isfile(ora_tab):
            try:
                # Since the oratab file can have multiple unique SID
                # entries that point to the same oracle home directory,
                # don't gather duplicate files
                path_list = set()

                with open(ora_tab, 'r', encoding='UTF-8') as ofile:
                    for line in ofile.read().splitlines():
                        if line.startswith('#') or not line.strip():
                            continue
                        path_list.add(line.split(':')[1])

                dbfiles = [
                    'dbs/init*.ora',
                    'dbs/spfile*.ora'
                ]

                self.add_copy_spec([
                    self.path_join(path, dbfile) for dbfile in dbfiles
                    for path in path_list])
            except IOError as ex:
                self._log_error(f'Could not open conf file {ora_tab}: {ex}')
                return
        else:
            self._log_warn("Could not locate oratab file. "
                           "Oracle data will not be collected.")

# vim: set et ts=4 sw=4 :
