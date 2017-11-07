#
# Copyright (c) 2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it would be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write the Free Software Foundation,
# Inc.,  51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

from sos.plugins import Plugin, RedHatPlugin


class Vdo(Plugin, RedHatPlugin):
    """Virtual Data Optimizer
    """

    plugin_name = 'vdo'
    profiles = ('storage',)
    packages = ('vdo',)
    files = (
        '/sys/kvdo',
        '/sys/uds',
        '/etc/vdoconf.yml',
        '/etc/vdoconf.xml'
    )

    def setup(self):
        self.add_copy_spec(self.files)
        self.add_cmd_output("vdo status")

# vim set et ts=4 sw=4 :
