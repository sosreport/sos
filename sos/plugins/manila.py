# Copyright (C) 2016 Red Hat, Inc., Vikrant Aggarwal <ervikrant06@gmail.com>

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
from sos.plugins import Plugin, RedHatPlugin


class ManilaPlugin(Plugin, RedHatPlugin):
    """Openstack Manila"""
    plugin_name = "manila"
    profiles = ('openstack', 'storage')
    option_list = [("list", "List NAS shares", "fast", False)]

    def setup(self):
        if self.get_option("list"):
            for os_var in ['OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME']:
                if os_var not in os.environ:
                    self.soslog.warning("%s not found in environment variables"
                                        " which is required" % (os_var))
                self.add_cmd_output("manila list")

        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/manila/")
        else:
            self.add_copy_spec_limit("/var/log/manila/*.log",
                                     sizelimit=self.get_option("log_size"))

        self.add_copy_spec("/etc/manila/manila.conf")
