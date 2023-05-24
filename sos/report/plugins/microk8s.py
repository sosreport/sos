# Copyright (C) 2023 Canonical Ltd.,
#                    David Negreira <david.negreira@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Microk8s(Plugin, UbuntuPlugin):
    """The Microk8s plugin collects the current status of the microk8s
    snap on a Ubuntu machine.

    It will collect logs from journald related to the snap.microk8s
    units as well as run microk8s commands to retrieve the configuration,
    status, version and loaded plugins.
    """

    short_desc = 'The lightweight Kubernetes'
    plugin_name = "microk8s"
    profiles = ('container',)

    packages = ('microk8s',)

    microk8s_cmd = "microk8s"

    def setup(self):
        self.add_journal(units="snap.microk8s.*")

        microk8s_subcmds = [
            'addons repo list',
            'config',
            'ctr plugins ls',
            'ctr plugins ls -d',
            'status',
            'version'
        ]

        self.add_cmd_output([
            f"microk8s {subcmd}" for subcmd in microk8s_subcmds
        ])

    def postproc(self):
        rsub = r'(certificate-authority-data:|token:)\s.*'
        self.do_cmd_output_sub("microk8s", rsub, r'\1 "**********"')

# vim: set et ts=4 sw=4
