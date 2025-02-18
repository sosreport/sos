# Copyright (C) 2018 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

from os.path import join
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class OmnipathClient(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'OmniPath Tools and Fast Fabric Client'

    plugin_name = 'omnipath_client'
    profiles = ('hardware',)

    packages = ('opa-basic-tools',)

    def setup(self):

        self.add_cmd_output([
            "opainfo",
            "opafabricinfo",
            "opahfirev",
            "opapmaquery",
            "opaportinfo",
            "opasaquery",
            "opasmaquery",
            "opashowmc",
            "opareports",
        ])

        # opacapture generates a tarball of given name we should collect;
        # rather than storing it somewhere under /var/tmp and copying it via
        # add_copy_spec, add it directly to sos_commands/<plugin> dir by
        # building a path argument using self.get_cmd_output_path().
        # This command calls 'depmod -a', so lets make sure we
        # specified the 'allow-system-changes' option before running it.
        if self.get_option('allow_system_changes'):
            opa_fullpath = join(self.get_cmd_output_path(), "opacapture.tgz")
            self.add_cmd_output(f"opacapture {opa_fullpath}",
                                changes=True)

# vim: set et ts=4 sw=4 :
