# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Docker(Plugin):

    """Docker containers
    """

    plugin_name = 'docker'
    profiles = ('container',)

    option_list = [
        ("all", "enable capture for all containers, even containers "
            "that have terminated", 'fast', False),
        ("logs", "capture logs for running containers",
            'fast', False),
        ("size", "capture image sizes for docker ps", 'slow', False)
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/docker/daemon.json",
            "/var/lib/docker/repositories-*"
        ])

        subcmds = [
            'events --since 24h --until 1s',
            'info',
            'images',
            'network ls',
            'ps',
            'ps -a',
            'stats --no-stream',
            'system df',
            'version',
            'volume ls'
        ]

        for subcmd in subcmds:
            self.add_cmd_output("docker %s" % subcmd)

        # separately grab ps -s as this can take a *very* long time
        if self.get_option('size'):
            self.add_cmd_output('docker ps -as')

        self.add_journal(units="docker")
        self.add_cmd_output("ls -alhR /etc/docker")

        nets = self.get_command_output('docker network ls')

        if nets['status'] == 0:
            n = [n.split()[1] for n in nets['output'].splitlines()[1:]]
            for net in n:
                self.add_cmd_output("docker network inspect %s" % net)

        ps_cmd = 'docker ps -q'
        if self.get_option('all'):
            ps_cmd = "%s -a" % ps_cmd

        img_cmd = 'docker images -q'
        insp = set()

        for icmd in [ps_cmd, img_cmd]:
            result = self.get_command_output(icmd)
            if result['status'] == 0:
                for con in result['output'].splitlines():
                    insp.add(con)

        insp = list(insp)
        if insp:
            for container in insp:
                self.add_cmd_output("docker inspect %s" % container)

            if self.get_option('logs'):
                for container in insp:
                    self.add_cmd_output("docker logs -t %s" % container)


class RedHatDocker(Docker, RedHatPlugin):

    packages = ('docker', 'docker-latest', 'docker-io', 'docker-engine')

    def setup(self):
        super(RedHatDocker, self).setup()

        self.add_copy_spec([
            "/etc/udev/rules.d/80-docker.rules",
            "/etc/containers/"
        ])


class UbuntuDocker(Docker, UbuntuPlugin):

    packages = ('docker.io', 'docker-engine')

    def setup(self):
        super(UbuntuDocker, self).setup()
        self.add_copy_spec([
            "/etc/default/docker",
            "/var/run/docker/libcontainerd/containerd/events.log"
        ])

# vim: set et ts=4 sw=4 :
