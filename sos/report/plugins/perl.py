# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Perl(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Perl runtime"""

    plugin_name = "perl"
    profiles = ('webserver', 'perl')
    verify_packages = ('perl.*',)

    def setup(self):
        self.add_cmd_output("perl -V")

# vim: set et ts=4 sw=4 :
