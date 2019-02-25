# Copyright (C) 2018 Red Hat, Inc. Daniel Walsh <dwalsh@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Podman(Plugin, RedHatPlugin, UbuntuPlugin):

    """Podman containers
    """

    plugin_name = 'podman'
    profiles = ('container',)
    packages = ('podman')

    option_list = [
        ("all", "enable capture for all containers, even containers "
            "that have terminated", 'fast', False),
        ("logs", "capture logs for running containers",
            'fast', False),
        ("size", "capture image sizes for podman ps", 'slow', False)
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/containers/registries.conf",
            "/etc/containers/storage.conf",
            "/etc/containers/mounts.conf",
            "/etc/containers/policy.json",
        ])

        subcmds = [
            'info',
            'images',
            'pod ps',
            'pod ps -a',
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

        self.add_cmd_output("ls -alhR /etc/cni")

        ps_cmd = 'podman ps -q'
        if self.get_option('all'):
            ps_cmd = "%s -a" % ps_cmd

        fmt = '{{lower .Repository}}:{{lower .Tag}} {{lower .ID}}'
        img_cmd = "podman images --format='%s'" % fmt
        vol_cmd = 'podman volume ls -q'

        containers = self._get_podman_list(ps_cmd)
        images = self._get_podman_list(img_cmd)
        volumes = self._get_podman_list(vol_cmd)

        for container in containers:
            self.add_cmd_output("podman inspect %s" % container)

        for img in images:
            name, img_id = img.strip().split()
            insp = name if 'none' not in name else img_id
            self.add_cmd_output("podman inspect %s" % insp)

        for vol in volumes:
            self.add_cmd_output("podman volume inspect %s" % vol)

        if self.get_option('logs'):
            for con in containers:
                self.add_cmd_output("podman logs -t %s" % con)

    def _get_podman_list(self, cmd):
        ret = []
        result = self.get_command_output(cmd)
        if result['status'] == 0:
            for ent in result['output'].splitlines():
                ret.append(ent)
        return ret

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
