# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Docker(Plugin):
    """Docker information
    """

    plugin_name = 'docker'
    docker_bin = "docker"

    def setup(self):
        self.add_copy_specs([
            "/var/lib/docker/repositories-*"
        ])

        self.add_cmd_outputs([
            "{0} info".format(self.docker_bin),
            "{0} ps".format(self.docker_bin),
            "{0} images".format(self.docker_bin)
        ])

        result = self.get_command_output("{0} ps".format(
            self.docker_bin))
        if result['status'] == 0:
            result['output'] = result['output'].split("\n")
            for line in result['output'][1:]:
                container_id = line.split(" ")[0]
                self.add_cmd_outputs([
                    "{0} logs {1}".format(self.docker_bin, container_id)
                ])


class RedHatDocker(Docker, RedHatPlugin):

    packages = ('docker-io',)

    def setup(self):
        super(RedHatDocker, self).setup()

        self.add_copy_specs([
            "/etc/udev/rules.d/80-docker.rules"
        ])


class UbuntuDocker(Docker, UbuntuPlugin):
    """ Docker information on Ubuntu
    """

    packages = ('docker.io',)

    # Name collision with another package requires docker binary rename
    docker_bin = 'docker.io'

    def setup(self):
        super(UbuntuDocker, self).setup()
        self.add_copy_specs([
            "/etc/default/docker.io"
        ])

# vim: et ts=4 sw=4
