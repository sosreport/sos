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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from glob import glob


class Puppet(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Puppet service
    """

    plugin_name = 'puppet'
    profiles = ('services',)

    def setup(self):
        self.add_copy_spec([
            "/etc/puppet/*.conf",
            "/etc/puppet/rack/*",
            "/etc/puppet/manifests/*",
            "/var/log/puppet/*.log",
        ])

    def postproc(self):
        for device_conf in glob("/etc/puppet/device.conf*"):
            self.do_file_sub(
                device_conf,
                r"(.*url*.ssh://.*:).*(@.*)",
                r"\1%s\2" % ('***')
            )

        return
# vim: et ts=4 sw=4
