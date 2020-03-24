# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class I18n(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Internationalization
    """

    plugin_name = 'i18n'
    profiles = ('system',)

    def setup(self):
        self.add_copy_spec([
            "/etc/X11/xinit/xinput.d/*",
            "/etc/locale.conf"
        ])
        self.add_cmd_output("locale", env={'LC_ALL': None})

# vim: set et ts=4 sw=4 :
