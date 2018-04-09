# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Rhui(Plugin, RedHatPlugin):
    """Red Hat Update Infrastructure
    """

    plugin_name = 'rhui'
    profiles = ('sysmgmt',)

    rhui_debug_path = "/usr/share/rh-rhua/rhui-debug.py"

    packages = ["rh-rhui-tools"]
    files = [rhui_debug_path]

    def setup(self):
        if self.is_installed("pulp-cds"):
            cds = "--cds"
        else:
            cds = ""

        rhui_debug_dst_path = self.get_cmd_output_path()
        self.add_cmd_output(
            "python %s %s --dir %s"
            % (self.rhui_debug_path, cds, rhui_debug_dst_path),
            suggest_filename="rhui-debug")
        return

# vim: set et ts=4 sw=4 :
