# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class X11(Plugin, IndependentPlugin):

    short_desc = 'X windowing system'

    plugin_name = 'x11'
    profiles = ('hardware', 'desktop')

    files = ('/etc/X11',)

    def setup(self):
        self.add_copy_spec([
            "/etc/X11",
            "/var/log/Xorg.*.log",
            "/var/log/Xorg.*.log.old",
            "/var/log/XFree86.*.log",
            "/var/log/XFree86.*.log.old",
        ])

        self.add_forbidden_path([
            "/etc/X11/X",
            "/etc/X11/fontpath.d"
        ])

        self.add_cmd_output([
            "xrandr --verbose"
        ])

        self.add_env_var([
            'DISPLAY',
            'DESKTOP_SESSION',
            'XDG_SESSION_TYPE',
            'XDG_SESSION_DESKTOP',
            'XMODIFIERS',
            'XDG_CURRENT_DESKTOP',
            'XDG_SEAT',
            'XDG_RUNTIME_DIR',
            'XAUTHORITY',
            'XDG_SESSION_PATH',
            'XDG_SEAT_PATH',
            'XDG_SESSION_ID'
        ])

# vim: set et ts=4 sw=4 :
