# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class SystemTap(Plugin, IndependentPlugin):

    short_desc = 'SystemTap dynamic instrumentation'

    plugin_name = 'systemtap'
    profiles = ('debug', 'performance')

    commands = ('stap',)
    packages = ('systemtap', 'systemtap-runtime')

    def setup(self):
        self.add_cmd_output([
            "stap -V 2",
            "uname -r",
            "stap-report"
        ])

# vim: set et ts=4 sw=4 :
