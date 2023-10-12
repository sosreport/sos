# Copyright (c) 2017 Bryan Quigley <bryan.quigley@canonical.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin

import re


class Snap(Plugin, IndependentPlugin):

    short_desc = 'Snap packages'

    plugin_name = 'snap'
    profiles = ('system', 'sysmgmt', 'packagemanager')
    packages = ('snapd',)
    services = ('snapd',)

    def setup(self):
        self.add_cmd_output("snap list --all", root_symlink="installed-snaps")
        self.add_cmd_output([
            "snap --version",
            "snap version",
            "snap whoami",
            "snap model --verbose",
            "snap model --serial --verbose",
            "snap services",
            "snap connections",
            "snap changes --abs-time",
            "snap validate",
            "snap debug state --abs-time --changes /var/lib/snapd/state.json",
            "snap debug stacktraces",
            "snap get system -d",
        ])

        all_pkgs = self.policy.package_manager.packages

        for pkg_name in all_pkgs:
            pkg = self.policy.package_manager.pkg_by_name(pkg_name)
            if pkg['pkg_manager'] == 'snap':
                self.add_cmd_output(f"snap connections {pkg['name']}")

        self.add_cmd_output("snap debug connectivity", timeout=10)

        # If we have gadget snaps, then we collect more files, this is
        # typically defined in the Notes column
        snap_list = self.exec_cmd('snap list')

        if snap_list['status'] == 0:
            output = snap_list['output']

            for line in output.splitlines()[1:]:
                if line == "":
                    continue
                snap_pkg = line.split()
                if re.match(r".*gadget.*$", snap_pkg[5]):
                    self.add_copy_spec([
                        f"/snap/{snap_pkg[0]}/current/meta/gadget.yaml",
                    ])

        snap_changes = self.collect_cmd_output('snap changes')

        if snap_changes['status'] == 0:
            output = snap_changes['output']

            for line in output.splitlines()[1:]:
                if line == "":
                    continue
                change = line.split()
                change_id, change_status = change[0], change[1]
                if change_status == "Doing" or change_status == "Error":
                    self.add_cmd_output(f"snap tasks {change_id} --abs-time")

# vim: set et ts=4 sw=4 :
