# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Hpasm(Plugin, IndependentPlugin):

    short_desc = 'HP Advanced Server Management'

    plugin_name = 'hpasm'
    profiles = ('system', 'hardware')

    packages = ('hp-health',)

    def setup(self):
        self.add_copy_spec("/var/log/hp-health/hpasmd.log")
        self.add_cmd_output([
            "hpasmcli -s 'show asr'",
            "hpasmcli -s 'show server'"
        ], timeout=0)

# vim: set et ts=4 sw=4 :
