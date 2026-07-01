# Copyright (C) 2026 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin)


class Foremanctl(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):

    short_desc = 'Foremanctl as foreman in pods'

    plugin_name = 'foremanctl'
    profiles = ('sysmgmt',)
    packages = ('foremanctl', )
    containers = ('foreman',)

    def setup(self):
        self.add_copy_spec([
            "/etc/foremanctl/inventory",
            "/var/lib/foremanctl/parameters.yaml",
            "/var/log/foremanctl/foremanctl.*log",
        ])

        self.add_cmd_output([
            "foremanctl features",
            "foremanctl health",
        ])

        self.add_dir_listing(["/var/lib/foremanctl/"], recursive=True)

    def postproc(self):
        # Scrub passwords, credentials, tokens, secrets, and keys
        self.do_path_regex_sub(
            "/var/lib/foremanctl/parameters.yaml",
            r"((.*)?(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r"\1********")

        # Scrub passwords from foremanctl logs
        self.do_path_regex_sub(
            "/var/log/foremanctl/foremanctl.*log*",
            r"(((passw|cred|token|secret)=)|(password ))(.*)",
            r"\1********")


# vim: set et ts=4 sw=4 :
