# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import pwd

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Mutter(Plugin, IndependentPlugin):
    """The Mutter plugin collects information about the GNOME display
    server configuration, including the persistent monitor layout and
    the live display state as reported by Mutter's D-Bus interface.

    Because Mutter runs inside a user session, the 'user' option must
    be set to the logged-in desktop user when sos is invoked as root.
    """

    short_desc = 'GNOME display server and Wayland compositor'

    plugin_name = 'mutter'
    profiles = ('desktop',)
    packages = ('mutter', 'mutter-common')

    option_list = [
        PluginOpt(
            'user',
            val_type=str,
            default='root',
            desc='Run Mutter D-Bus queries as a specific user',
        ),
    ]

    def setup(self):
        user = self.get_option('user')
        try:
            pwd_user = pwd.getpwnam(user)
        except KeyError:
            self._log_warn(
                f'User "{user}" does not exist, will not collect Mutter '
                'information. Use `-k mutter.user` to specify the '
                'desktop session user')
            return

        self.add_copy_spec('/etc/xdg/monitors.xml')

        home_dir = pwd_user.pw_dir
        self.add_copy_spec(f'{home_dir}/.config/monitors.xml')

        self.add_cmd_output(
            'gdbus call -e '
            '-d org.gnome.Mutter.DisplayConfig '
            '-o /org/gnome/Mutter/DisplayConfig '
            '-m org.gnome.Mutter.DisplayConfig.GetCurrentState',
            runas=user
        )

# vim: set et ts=4 sw=4 :
