# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Fwupd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """fwupd information
    """

    plugin_name = 'fwupd'
    profiles = ('system', )

    packages = ('fwupd',)

    def setup(self):
        self.add_cmd_output([
            "fwupdmgr get-approved-firmware",
            "fwupdmgr get-devices --no-unreported-check",
            "fwupdmgr get-history",
            "fwupdmgr get-remotes",
            # collect json format using fwupdagent
            "/usr/libexec/fwupd/fwupdagent get-devices",
            "/usr/libexec/fwupd/fwupdagent get-updates",
        ])

        self.add_copy_spec("/etc/fwupd")

        self.add_journal(units="fwupd")

    def postproc(self):
        self.do_path_regex_sub(
            "/etc/fwupd/remotes.d/*",
            r"Password=(.*)",
            r"Password=********"
        )

        self.do_file_sub(
            "/etc/fwupd/redfish.conf",
            r"Password=(.*)",
            r"Password=********"
        )


# vim: et ts=4 sw=4
