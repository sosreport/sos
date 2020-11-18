# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class OpenCL(Plugin, IndependentPlugin):

    short_desc = 'OpenCL'

    plugin_name = 'opencl'
    profiles = ('hardware', 'desktop', 'gpu')
    files = ('/usr/bin/clinfo',)

    def setup(self):
        self.add_cmd_output([
            "clinfo",
        ])

# vim: set et ts=4 sw=4 :
