# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Docker(Plugin):

    """Docker containers
    """

    plugin_name = 'docker'
    profiles = ('virt',)
    docker_cmd = "docker"

    option_list = [
        ("all", "enable capture for all containers, even containers "
            "that have terminated", 'fast', False),
        ("logs", "capture logs for running containers",
            'fast', False),
        ("size", "capture image sizes for docker ps", 'slow', False)
    ]

    def setup(self):
        self.add_copy_spec([
            "/var/lib/docker/repositories-*"
        ])

        subcmds = [
            'info',
            'images',
            'network ls',
            'ps',
            'ps -a',
            'stats --no-stream',
            'version'
        ]

        for subcmd in subcmds:
            self.add_cmd_output(
                "{0} {1}".format(self.docker_cmd, subcmd)
            )

        # separately grab ps -s as this can take a *very* long time
        if self.get_option('size'):
            self.add_cmd_output('{0} ps -as'.format(self.docker_cmd))

        self.add_journal(units="docker")
        self.add_cmd_output("ls -alhR /etc/docker")

        net_cmd = '{0} network ls'.format(self.docker_cmd)
        nets = self.get_command_output(net_cmd)

        if nets['status'] == 0:
            n = [n.split()[1] for n in nets['output'].splitlines()[1:]]
            for net in n:
                self.add_cmd_output(
                    "{0} network inspect {1}".format(
                        self.docker_cmd,
                        net
                    )
                )

        ps_cmd = "{0} ps -q".format(self.docker_cmd)
        if self.get_option('all'):
            ps_cmd = "{0} -a".format(ps_cmd)

        img_cmd = '{0} images -q'.format(self.docker_cmd)
        insp = set()

        for icmd in [ps_cmd, img_cmd]:
            result = self.get_command_output(icmd)
            if result['status'] == 0:
                for con in result['output'].splitlines():
                    insp.add(con)

        insp = list(insp)
        if insp:
            for container in insp:
                self.add_cmd_output(
                    "{0} inspect {1}".format(
                        self.docker_cmd,
                        container
                    )
                )
            if self.get_option('logs'):
                for container in containers:
                    self.add_cmd_output(
                        "{0} logs {1}".format(
                            self.docker_cmd,
                            container
                        )
                    )


class RedHatDocker(Docker, RedHatPlugin):

    packages = ('docker', 'docker-latest', 'docker-io', 'docker-engine')

    def setup(self):
        super(RedHatDocker, self).setup()

        self.add_copy_spec([
            "/etc/udev/rules.d/80-docker.rules"
        ])


class UbuntuDocker(Docker, UbuntuPlugin):

    packages = ('docker.io', 'docker-engine')

    # Name collision with another package requires docker binary rename
    docker_cmd = 'docker.io'

    def setup(self):
        super(UbuntuDocker, self).setup()
        self.add_copy_spec([
            "/etc/default/docker.io"
        ])

# vim: set et ts=4 sw=4 :
