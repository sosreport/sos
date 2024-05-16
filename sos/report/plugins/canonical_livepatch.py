# Copyright (c) 2016 Bryan Quigley <bryan.quigley@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class CanonicaLivepatch(Plugin, UbuntuPlugin):

    short_desc = 'Canonical Livepatch Service'

    plugin_name = 'canonical_livepatch'
    profiles = ('system', 'kernel')
    commands = ('canonical-livepatch',)
    services = ('snap.canonical-livepatch.canonical-livepatchd',)

    def setup(self):
        self.add_cmd_output([
            "canonical-livepatch status --verbose",
            "canonical-livepatch --version",
            "canonical-livepatch config",
        ])

    def postproc(self):
        self.do_cmd_private_sub("canonical-livepatch config")

# vim: set et ts=4 sw=4 :
