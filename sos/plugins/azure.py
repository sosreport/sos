# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
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

from sos.plugins import Plugin, UbuntuPlugin, RedHatPlugin


class Azure(Plugin, UbuntuPlugin, RedHatPlugin):
    """ Microsoft Azure client
    """

    plugin_name = 'azure'
    profiles = ('virt',)
    packages = ('walinuxagent',)

    def setup(self):
        self.add_copy_spec([
            "/var/log/waagent*",
            "/var/lib/cloud",
            "/etc/default/kv-kvp-daemon-init",
            "/etc/waagent.conf",
            "/sys/module/hv_netvsc/parameters/ring_size",
            "/sys/module/hv_storvsc/parameters/storvsc_ringbuffer_size"
        ])

# vim: set et ts=4 sw=4 :
