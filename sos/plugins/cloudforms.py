## Copyright (C) 2012 Red Hat Inc., Bryn M. Reeves <bmr@redhat.com>
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

from sos.plugins import Plugin, RedHatPlugin
import os

class Cloudforms(Plugin, RedHatPlugin):
    """CloudForms related information
    """

    packages = ["katello", "katello-common",
                    "katello-headpin", "aeoleus-conductor"]
    files = ["/usr/share/katello/script/katello-debug",
                "aeolus-debug"]

    def setup(self):
        katello_debug = "/usr/share/katello/script/katello-debug"
        aeolus_debug = "aeolus-debug"
        if os.path.isfile(katello_debug):
            katello_debug_path = os.path.join(self.commons['dstroot'],"katello-debug")
            self.add_cmd_output("%s --notar -d %s" % (katello_debug, katello_debug_path))
        if os.path.isfile(aeolus_debug):
            aeolus_debug_path = os.path.join(self.commons['dstroot'],"aeolus-debug")
            self.add_cmd_output("%s --notar -d %s" % (aeolus_debug, aeolus_debug_path))

