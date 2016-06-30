# Copyright (C) 2016 Red Hat, Inc., Tomas Tomecek <ttomecek@redhat>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
    SuSEPlugin


class Npm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, SuSEPlugin):
    """
    Get info about available npm modules
    """

    requires_root = False
    plugin_name = 'npm'
    profiles = ('system',)

    # in Fedora, Debian, Ubuntu and Suse the package is called npm
    packages = ('npm',)

    def setup(self):
        # stderr output is already part of the json, key "problems"
        self.add_cmd_output(
            "npm ls -g --json",
            suggest_filename="npm-list",
            stderr=False
        )


class NpmViaNodeJS(Npm):
    """
    some distribution methods don't provide 'npm' via npm package
    """

    # upstream doesn't have an npm package, it's just nodejs
    # also in Fedora 24+ it is just nodejs, no npm package
    packages = ('nodejs', )

# TODO: in RHEL npm and nodejs is available via software collections
#       this should be handled separately

# vim: set et ts=4 sw=4 :
