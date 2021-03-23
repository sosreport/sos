# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Flatpak(Plugin, IndependentPlugin):

    short_desc = 'Flatpak'

    plugin_name = 'flatpak'
    profiles = ('sysmgmt', 'packagemanager')
    commands = ("flatpak",)
    packages = ("flatpak",)

    def setup(self):
        self.add_cmd_output([
            "flatpak --version",
            "flatpak --default-arch",
            "flatpak --supported-arches",
            "flatpak --gl-drivers",
            "flatpak --installations",
            "flatpak --print-updated-env",
            "flatpak config",
            "flatpak remote-list --show-details",
            "flatpak list --runtime --show-details",
            "flatpak list --app --show-details",
            "flatpak history --columns=all",
        ])
        if self.get_option("verify"):
            self.add_cmd_output("flatpak repair --dry-run")

# vim: set et ts=4 sw=4 :
