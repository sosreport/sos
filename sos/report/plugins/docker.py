# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, UbuntuPlugin,
                                SoSPredicate, CosPlugin)


class Docker(Plugin, CosPlugin):

    short_desc = 'Docker containers'
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

        self.add_env_var([
            'HTTP_PROXY',
            'HTTPS_PROXY',
            'NO_PROXY',
            'ALL_PROXY',
            'DOCKER_BUILD_PROXY',
            'DOCKER_RUN_PROXY'
        ])

        self.add_journal(units="docker")
        self.add_cmd_output("ls -alhR /etc/docker")

        self.set_cmd_predicate(SoSPredicate(self, services=["docker"]))

        subcmds = [
            'events --since 24h --until 1s',
            'info',
            'images',
            'ps',
            'ps -a',
            'stats --no-stream',
            'version',
            'volume ls'
        ]

        for subcmd in subcmds:
            self.add_cmd_output("docker %s" % subcmd)

        # separately grab these separately as they can take a *very* long time
        if self.get_option('size'):
            self.add_cmd_output('docker ps -as', priority=100)
            self.add_cmd_output('docker system df', priority=100)

        nets = self.collect_cmd_output('docker network ls')

        if nets['status'] == 0:
            n = [n.split()[1] for n in nets['output'].splitlines()[1:]]
            for net in n:
                self.add_cmd_output("docker network inspect %s" % net)

        containers = [
            c[0] for c in self.get_containers(runtime='docker',
                                              get_all=self.get_option('all'))
        ]
        images = self.get_container_images(runtime='docker')
        volumes = self.get_container_volumes(runtime='docker')

        for container in containers:
            self.add_cmd_output("docker inspect %s" % container,
                                subdir='containers')
            if self.get_option('logs'):
                self.add_cmd_output("docker logs -t %s" % container,
                                    subdir='containers')

        for img in images:
            name, img_id = img
            insp = name if 'none' not in name else img_id
            self.add_cmd_output("docker inspect %s" % insp, subdir='images')

        for vol in volumes:
            self.add_cmd_output("docker volume inspect %s" % vol,
                                subdir='volumes')

    def postproc(self):
        # Attempts to match key=value pairs inside container inspect output
        # for potentially sensitive items like env vars that contain passwords.
        # Typically, these will be seen in env elements or similar, and look
        # like this:
        #             "Env": [
        #                "mypassword=supersecret",
        #                "container=oci"
        #             ],
        # This will mask values when the variable name looks like it may be
        # something worth obfuscating.

        env_regexp = r'(?P<var>(pass|key|secret|PASS|KEY|SECRET).*?)=' \
                      '(?P<value>.*?)"'
        self.do_cmd_output_sub('*inspect*', env_regexp,
                               r'\g<var>=********"')


class RedHatDocker(Docker, RedHatPlugin):

    packages = ('docker', 'docker-latest', 'docker-io', 'docker-engine',
                'docker-ce', 'docker-ee')

    def setup(self):
        super(RedHatDocker, self).setup()

        self.add_copy_spec([
            "/etc/udev/rules.d/80-docker.rules",
            "/etc/containers/"
        ])


class UbuntuDocker(Docker, UbuntuPlugin):

    packages = ('docker.io', 'docker-engine', 'docker-ce', 'docker-ee')

    def setup(self):
        super(UbuntuDocker, self).setup()
        self.add_copy_spec([
            "/etc/containerd/",
            "/etc/default/docker",
            "/run/docker/libcontainerd/containerd/events.log"
        ])

# vim: set et ts=4 sw=4 :
