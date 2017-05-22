# Copyright (C) 2016 Red Hat, Inc., Tomas Tomecek <ttomecek@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
    SuSEPlugin


class NodeJS(Plugin, RedHatPlugin, SuSEPlugin):
    """ Get runtime version of NodeJS """

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
