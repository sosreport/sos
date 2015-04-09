# Copyright (C) 2015 Red Hat, Inc.

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

from sos.plugins import Plugin, RedHatPlugin
import os.path


class AtomicHost(Plugin, RedHatPlugin):
    """ Atomic Host """

    plugin_name = "atomichost"
    option_list = [("info", "gather atomic info for each image",
                    "fast", False)]

    def check_enabled(self):
        if not os.path.exists("/host/etc/system-release-cpe"):
            return False
        cpe = open("/host/etc/system-release-cpe", "r").readlines()
        return ':atomic-host' in cpe[0]

    def setup(self):
        self.add_copy_spec("/etc/ostree/remotes.d")
        self.add_cmd_output("atomic host status")

        if self.get_option('info'):
            images = self.get_command_output("docker images -q")
            for image in set(
                            images['output'].splitlines()
                        ):
                if image:
                    self.add_cmd_output("atomic info {0}".format(image))
