# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Vulkan(Plugin, IndependentPlugin):

    short_desc = 'Vulkan'

    plugin_name = 'vulkan'
    profiles = ('hardware', 'desktop', 'gpu')
    files = ('/usr/bin/vulkaninfo',)

    def setup(self):
        self.add_cmd_output([
            "vulkaninfo",
        ])

# vim: set et ts=4 sw=4 :
