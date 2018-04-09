# Copyright (C) 2014 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Python(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Python runtime
    """

    plugin_name = 'python'
    profiles = ('system',)

    packages = ('python',)

    def setup(self):
        self.add_cmd_output("python -V", suggest_filename="python-version")

# vim: set et ts=4 sw=4 :
