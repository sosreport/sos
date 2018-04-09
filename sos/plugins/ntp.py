# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
