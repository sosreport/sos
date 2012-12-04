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

class cloudforms(Plugin, RedHatPlugin):
    """CloudForms related information
    """

    packages = ["katello"]

    def setup(self):
	katello_debug = "/usr/share/katello/scripts/katello-debug"
        self.collectExtOutput("%s -d %s" \
            % (katello_debug, 
		os.path.join(self.cInfo['dstroot'],"cloudforms")))
