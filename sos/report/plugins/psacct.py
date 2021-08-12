# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)


class Psacct(Plugin):

    short_desc = 'Process accounting information'
    plugin_name = "psacct"
    profiles = ('system',)

    option_list = [
        PluginOpt('all', default=False, desc='collect all accounting files')
    ]

    packages = ("psacct", )


class RedHatPsacct(Psacct, RedHatPlugin):

    packages = ("psacct", )

    def setup(self):
        super(RedHatPsacct, self).setup()
        self.add_copy_spec("/var/account/pacct")
        if self.get_option("all"):
            self.add_copy_spec("/var/account/pacct*.gz")


class DebianPsacct(Psacct, DebianPlugin, UbuntuPlugin):

    packages = ("acct", )

    def setup(self):
        super(DebianPsacct, self).setup()
        self.add_copy_spec(["/var/log/account/pacct", "/etc/default/acct"])
        if self.get_option("all"):
            self.add_copy_spec("/var/log/account/pacct*.gz")

# vim: set et ts=4 sw=4 :
