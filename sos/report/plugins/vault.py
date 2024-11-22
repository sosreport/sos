# Copyright (C) 2023 Canonical Ltd., Arif Ali <arif.ali@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Vault(Plugin, UbuntuPlugin):
    """The Vault plugin collects the current status of the vault
    snap on a Ubuntu machine.

    It will collect logs from journal, vault status and configuration
    """

    short_desc = 'Manage access to secrets and protect sensitive data'

    plugin_name = 'vault'
    profiles = ('sysmgmt', 'security')
    services = ('vault',)
    package = ('vault',)

    def setup(self):

        vault_cfg = "/var/snap/vault/common/vault.hcl"

        self.add_copy_spec(vault_cfg)

        try:
            with open(vault_cfg, 'r', encoding='UTF-8') as cfile:
                for line in cfile.read().splitlines():
                    if not line:
                        continue
                    words = line.split('=')
                    if words[0].strip() == 'api_addr':
                        api_addr = words[1].strip('\" ')
                        self.add_cmd_output("vault status",
                                            env={'VAULT_ADDR': api_addr})
        except IOError as error:
            self._log_error(f'Could not open conf file {vault_cfg}: {error}')

    def postproc(self):
        self.do_file_sub(
            "/var/snap/vault/common/vault.hcl",
            r"(password\s?=\s?).*",
            r"\1******"
        )

# vim: set et ts=4 sw=4 :
