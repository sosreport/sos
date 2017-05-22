# Copyright (c) 2016 Bryan Quigley <bryan.quigley@canonical.com>

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

from sos.plugins import Plugin, UbuntuPlugin


class CanonicaLivepatch(Plugin, UbuntuPlugin):
    """Canonical Livepatch Service
    """

    plugin_name = 'canonical_livepatch'
    profiles = ('system', 'kernel')
    files = ('/snap/bin/canonical-livepatch')

    def setup(self):
        self.add_cmd_output([
            "systemctl status snap.canonical-livepatch.canonical-livepatchd",
            "snap run canonical-livepatch status --verbose",
            "snap run canonical-livepatch --version"
        ])

# vim: set et ts=4 sw=4 :
