# Copyright (C) 2018 Red Hat, Inc. Daniel Walsh <dwalsh@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin, PluginOpt


class Podman(Plugin, RedHatPlugin, UbuntuPlugin):
    """Podman is a daemonless container management engine, and this plugin is
    meant to provide diagnostic information for both the engine and the
    containers that podman is managing.

    General status information will be collected from podman commands, while
    detailed inspections of certain components will provide more insight
    into specific container problems. This detailed inspection is provided for
    containers, images, networks, and volumes. Per-entity inspections will be
    recorded in subdirs within sos_commands/podman/ for each of those types.
    """

    short_desc = 'Podman containers'
    plugin_name = 'podman'
    profiles = ('container',)
    packages = ('podman',)

    option_list = [
        PluginOpt('all', default=False,
                  desc='collect for all containers, even terminated ones',
                  long_desc=(
                    'Enable collection for all containers that exist on the '
                    'system regardless of their running state. This may cause '
                    'a significant increase in sos archive size, especially '
                    'when combined with the \'logs\' option.')),
        PluginOpt('logs', default=False,
                  desc='collect stdout/stderr logs for containers',
                  long_desc=(
                    'Capture \'podman logs\' output for discovered containers.'
                    ' This may be useful or not depending on how/if the '
                    'container produces stdout/stderr output. Use cautiously '
                    'when also using the \'all\' option.')),
        PluginOpt('size', default=False,
                  desc='collect image sizes for podman ps')
    ]

    def setup(self):
        self.add_env_var([
            'HTTP_PROXY',
            'HTTPS_PROXY',
            'NO_PROXY',
            'ALL_PROXY'
        ])

        self.add_cmd_tags({
            'podman images': 'podman_list_images',
            'podman ps.*': 'podman_list_containers'
        })

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
            self.add_cmd_output('podman ps -as', priority=100)

        self.add_cmd_output([
            "ls -alhR /etc/cni",
            "ls -alhR /etc/containers"
        ])

        pnets = self.collect_cmd_output('podman network ls',
                                        tags='podman_list_networks')
        if pnets['status'] == 0:
            nets = [pn.split()[0] for pn in pnets['output'].splitlines()[1:]]
            self.add_cmd_output([
                "podman network inspect %s" % net for net in nets
            ], subdir='networks', tags='podman_network_inspect')

        containers = [
            c[0] for c in self.get_containers(runtime='podman',
                                              get_all=self.get_option('all'))
        ]
        images = self.get_container_images(runtime='podman')
        volumes = self.get_container_volumes(runtime='podman')

        for container in containers:
            self.add_cmd_output("podman inspect %s" % container,
                                subdir='containers',
                                tags='podman_container_inspect')

        for img in images:
            name, img_id = img
            insp = name if 'none' not in name else img_id
            self.add_cmd_output("podman inspect %s" % insp, subdir='images',
                                tags='podman_image_inspect')

        for vol in volumes:
            self.add_cmd_output("podman volume inspect %s" % vol,
                                subdir='volumes',
                                tags='podman_volume_inspect')

        if self.get_option('logs'):
            for con in containers:
                self.add_cmd_output("podman logs -t %s" % con,
                                    subdir='containers', priority=50)

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
