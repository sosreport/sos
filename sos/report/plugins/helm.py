# Copyright (C) 2025 Canonical Ltd.,
#                    Bryan Fraschetti <bryan.fraschetti@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Helm(Plugin, IndependentPlugin):
    """The Helm plugin collects information about the currently installed
    Helm charts, plugins, and repositories used in delpoyments
    """

    short_desc = 'The k8s templating and deployment manager'
    plugin_name = "helm"
    profiles = ('container', 'packagemanager')

    packages = ('helm',)

    helm_cmd = "helm"

    def setup(self):
        helm_subcmds = [
            'repo list',
            'plugin list',
            'list -a',
            'version',
        ]

        self.add_cmd_output([
            f"{self.helm_cmd} {subcmd}" for subcmd in helm_subcmds
        ])

# vim: set et ts=4 sw=4 :
