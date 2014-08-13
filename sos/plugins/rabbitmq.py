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


class RabbitMQ(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """rabbitmq related information
    """
    plugin_name = 'rabbitmq'
    files = ('/etc/rabbitmq/rabbitmq.conf',)
    packages = ('rabbitmq-server',)

    def setup(self):
        self.add_cmd_output("rabbitmqctl report")
        self.add_copy_spec("/etc/rabbitmq/*")
        self.add_copy_spec_limit("/var/log/rabbitmq/*",
                                 sizelimit=self.get_option('log_size'))
# vim: et ts=4 sw=4
