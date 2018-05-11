# Copyright (C) 2018 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

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

import os
from sos.plugins import Plugin, RedHatPlugin


class Fibrechannel(Plugin, RedHatPlugin):
    '''Collects information on fibrechannel devices, if present'''

    plugin_name = 'fibrechannel'
    profiles = ('hardware', 'storage', 'system')
    files = ('/sys/class/fc_host')

    def setup(self):

        devs = []
        dirs = [
            '/sys/class/fc_host/',
            '/sys/class/fc_remote_ports/',
            '/sys/class/fc_transport/'
        ]

        for loc in dirs:
            devs.extend([loc + device for device in os.listdir(loc)])

        if devs:
            self.add_udev_info(devs, attrs=True)

# vim: set et ts=4 sw=4 :
