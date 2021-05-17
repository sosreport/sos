# Copyright (C) 2018 Red Hat, Inc. Daniel Walsh <dwalsh@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Podman(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Podman containers'
    plugin_name = 'podman'
    profiles = ('container',)
    packages = ('podman',)

    option_list = [
        ("all", "enable capture for all containers, even containers "
            "that have terminated", 'fast', False),
        ("logs", "capture logs for running containers",
            'fast', False),
        ("size", "capture image sizes for podman ps", 'slow', False)
    ]

    def setup(self):
        self.add_env_var([
            'HTTP_PROXY',
            'HTTPS_PROXY',
            'NO_PROXY',
            'ALL_PROXY'
        ])

        subcmds = [
            'info',
            'images',
            'images --digests',
            'pod ps',
            'port --all',
            'ps',
            'ps -a',
            'stats --no-stream --all',
            'version',
            'volume ls'
        ]

        self.add_cmd_output(["podman %s" % s for s in subcmds])

        # separately grab ps -s as this can take a *very* long time
        if self.get_option('size'):
            self.add_cmd_output('podman ps -as')

        self.add_cmd_output([
            "ls -alhR /etc/cni",
            "ls -alhR /etc/containers"
        ])

        pnets = self.collect_cmd_output('podman network ls')
        if pnets['status'] == 0:
            nets = [pn.split()[0] for pn in pnets['output'].splitlines()[1:]]
            self.add_cmd_output([
                "podman network inspect %s" % net for net in nets
            ], subdir='networks')

        containers = [
            c[0] for c in self.get_containers(runtime='podman',
                                              get_all=self.get_option('all'))
        ]
        images = self.get_container_images(runtime='podman')
        volumes = self.get_container_volumes(runtime='podman')

        for container in containers:
            self.add_cmd_output("podman inspect %s" % container,
                                subdir='containers')

        for img in images:
            name, img_id = img
            insp = name if 'none' not in name else img_id
            self.add_cmd_output("podman inspect %s" % insp, subdir='images')

        for vol in volumes:
            self.add_cmd_output("podman volume inspect %s" % vol,
                                subdir='volumes')

        if self.get_option('logs'):
            for con in containers:
                self.add_cmd_output("podman logs -t %s" % con,
                                    subdir='containers')

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

# vim: set et ts=4 sw=4 :
