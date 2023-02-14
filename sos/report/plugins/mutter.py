# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from pathlib import Path
from sos.report.plugins import Plugin, IndependentPlugin


class Mutter(Plugin, IndependentPlugin):

    short_desc = 'GNOME X11 window manager and Wayland compositor'

    plugin_name = 'mutter'
    profiles = ('desktop',)
    packages = ('mutter',)

    def setup(self):
        # Get the monitors.xml file that persists the monitor setup
        monitors_xml = os.path.join(Path.home(), '.config', 'monitors.xml')
        self.add_copy_spec(monitors_xml)

        # Call mutter's DisplayConfig.GetCurrentState() to get even more info.
        # Note that both of these calls do the same thing, but one can be
        # parsed into a GVariant, while the other is easier to read immediately
        self.add_cmd_output('gdbus call -e '
                            '-d org.gnome.Mutter.DisplayConfig '
                            '-o /org/gnome/Mutter/DisplayConfig '
                            '-m org.gnome.Mutter.DisplayConfig.GetCurrentState'
                            )
        self.add_cmd_output('dbus-send --session --print-reply '
                            '--dest=org.gnome.Mutter.DisplayConfig '
                            '/org/gnome/Mutter/DisplayConfig '
                            'org.gnome.Mutter.DisplayConfig.GetCurrentState'
                            )

# vim: set et ts=4 sw=4 :
