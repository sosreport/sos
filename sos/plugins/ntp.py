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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ntp(Plugin):
    """Network time protocol
    """

    plugin_name = "ntp"
    profiles = ('system', 'services')

    packages = ('ntp',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ntp.conf",
            "/etc/ntp/step-tickers",
            "/etc/ntp/ntpservers"
        ])
        self.add_cmd_output([
            "ntptime",
            "ntpq -pn",
            "ntpq -c as"
        ])

        ids = self.get_command_output('ntpq -c as')
        if ids['status'] == 0:
            for asid in [i.split()[1] for i in ids['output'].splitlines()[3:]]:
                self.add_cmd_output("ntpq -c 'rv %s'" % asid)


class RedHatNtp(Ntp, RedHatPlugin):

    def setup(self):
        super(RedHatNtp, self).setup()
        self.add_copy_spec("/etc/sysconfig/ntpd")
        self.add_cmd_output("ntpstat")


class DebianNtp(Ntp, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianNtp, self).setup()
        self.add_copy_spec('/etc/default/ntp')


# vim: set et ts=4 sw=4 :
