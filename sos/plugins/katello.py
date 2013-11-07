## Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin

class Katello(Plugin, RedHatPlugin):
    """Katello project related information
    """

    plugin_name = 'katello'
    packages = ('katello', 'katello-common', 'katello-headpin')

    def setup(self):
        katello_debug_path = os.path.join(
            self.get_cmd_path(),"katello-debug")
        self.add_cmd_output("%s --notar -d %s"
            % ("katello-debug", katello_debug_path))
