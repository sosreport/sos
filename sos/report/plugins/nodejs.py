# Copyright (C) 2016 Red Hat, Inc., Tomas Tomecek <ttomecek@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, SuSEPlugin)


class NodeJS(Plugin, RedHatPlugin, SuSEPlugin):

    short_desc = 'NodeJS runtime version'

    plugin_name = 'nodejs'
    profiles = ('system',)

    packages = ('nodejs',)

    def setup(self):
        # we could get much more info with:
        #   p = require("process"); console.log(p)
        # unfortunately 'process' module is not available on 0.10
        self.add_cmd_output("node -v", suggest_filename="nodejs-version")


class NodeJSUbuntu(NodeJS, UbuntuPlugin, DebianPlugin):
    """
    Ubuntu/Debian require nodejs-legacy package in order to
    have a node executable
    """
    packages = ('nodejs', 'nodejs-legacy')

# vim: set et ts=4 sw=4 :
