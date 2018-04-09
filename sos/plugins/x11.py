# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class X11(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """X windowing system
    """

    plugin_name = 'x11'
    profiles = ('hardware', 'desktop')

    files = ('/etc/X11',)

    def setup(self):
        self.add_copy_spec([
            "/etc/X11",
            "/var/log/Xorg.*.log",
            "/var/log/XFree86.*.log",
        ])

        self.add_forbidden_path([
            "/etc/X11/X",
            "/etc/X11/fontpath.d"
        ])

        self.add_cmd_output([
            "xrandr --verbose"
        ])

# vim: set et ts=4 sw=4 :
