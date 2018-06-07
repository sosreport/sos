# systool.py
# Copyright (C) 2007-2014 Red Hat, Inc., Jon Magrini <jmagrini@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import os.path
from sos.plugins import Plugin, RedHatPlugin, os

class sysfsutils(Plugin, RedHatPlugin):
    """View system device information by bus, class, and topology
    """

    plugin_name = 'sysfsutils'
    profiles = 'storage'
    packages = 'sysfsutils'
    kernel_mods = ('scsi_transport_fc', 'scsi_tgt')

    def get_systool_output(self):
        """ systool fc specific information - commands
        """
        self.add_cmd_output([
            "/usr/bin/systool -c fc_host -v",
            "/usr/bin/systool -c fc_remote_ports -v"
        ])

    def setup(self):
        # If sysfsutils is installed collect data
        if os.path.isfile("/usr/bin/systool"):
            self.add_custom_text("sysfsutils is installed.<br>")
            self.get_systool_output()
