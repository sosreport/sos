# Copyright (C) 2018 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.report.plugins import Plugin, RedHatPlugin


class OmnipathManager(Plugin, RedHatPlugin):

    short_desc = 'OmniPath Fabric Manager'

    plugin_name = 'omnipath_manager'
    profiles = ('hardware',)

    packages = ('opa-fm',)

    def setup(self):

        # Use absolute paths for the opa-fm binaries since they are installed
        # in a non-standard location (sos policies do not evaluate drop-in
        # files from /etc/profile.d).
        self.add_cmd_output([
            "/usr/lib/opa-fm/bin/config_check -v -d -s",
            "/usr/lib/opa-fm/bin/fm_cmdall smAdaptiveRouting",
            "/usr/lib/opa-fm/bin/fm_cmdall smLooptestShowConfig",
            "/usr/lib/opa-fm/bin/fm_cmdall smLooptestShowTopology",
            "/usr/lib/opa-fm/bin/fm_cmdall smLooptestShowSwitchLft",
            "/usr/lib/opa-fm/bin/fm_cmdall smLooptestShowLoopPaths",
            "/usr/lib/opa-fm/bin/fm_cmdall pmShowCounters",
            "/usr/lib/opa-fm/bin/fm_cmdall smShowCounters",
        ])

        # fm_capture generates a dated tgz file in the current directory only
        # so change dir to sos_commands/<plugin>, collect the tarball directly
        # there now, and change dir back. This is unfortunate but is the only
        # way to collect this since fm_capture has no option to set the output
        # path or file name.
        #
        # This may also need to be amended for other distributions if these
        # binaries are placed in an alternative location (e.g. /usr/libexec).
        self.add_cmd_output("/usr/lib/opa-fm/bin/fm_capture",
                            runat=self.get_cmd_output_path())

        self.add_copy_spec("/etc/opa-fm/opafm.xml")

# vim: set et ts=4 sw=4 :
