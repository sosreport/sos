# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class TPM2(Plugin, IndependentPlugin):
    """
    Collects information about TPM2 module installed on host system.

    This plugin will capture data using tpm2_tools
    """

    short_desc = 'Trusted Platform Module 2.0'
    plugin_name = 'tpm2'
    profiles = ('security', 'system', 'storage', 'hardware')
    packages = ('tpm2-tools',)

    def setup(self):
        self.add_cmd_output([
            'tpm2_getcap properties-variable',
            'tpm2_getcap properties-fixed',
            'tpm2_nvreadpublic',
            'tpm2_readclock'
        ])

# vim: set et ts=4 sw=4 :
