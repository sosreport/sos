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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class RabbitMQ(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """RabbitMQ messaging service
    """
    plugin_name = 'rabbitmq'
    profiles = ('services',)
    var_puppet_gen = "/var/lib/config-data/puppet-generated/rabbitmq"
    files = (
        '/etc/rabbitmq/rabbitmq.conf',
        var_puppet_gen + '/etc/rabbitmq/rabbitmq.config'
    )
    packages = ('rabbitmq-server',)

    def setup(self):
        container_status = self.get_command_output(
            "docker ps -a --format='{{ .Names }}'")

        in_container = False
        container_names = []
        if container_status['status'] == 0:
            for line in container_status['output'].splitlines():
                if line.startswith("rabbitmq"):
                    in_container = True
                    container_names.append(line)

        if in_container:
            for container in container_names:
                self.add_cmd_output('docker logs {0}'.format(container))
                self.add_cmd_output(
                    'docker exec -t {0} rabbitmqctl report'
                    .format(container)
                )
        else:
            self.add_cmd_output("rabbitmqctl report")

        self.add_copy_spec([
            "/etc/rabbitmq/*",
            self.var_puppet_gen + "/etc/rabbitmq/*",
            self.var_puppet_gen + "/etc/security/limits.d/",
            self.var_puppet_gen + "/etc/systemd/"
        ])
        self.add_copy_spec([
            "/var/log/rabbitmq/*",
            "/var/log/containers/rabbitmq/*"
        ], sizelimit=self.get_option('log_size'))


# vim: set et ts=4 sw=4 :
