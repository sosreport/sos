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
            'stats --no-stream',
            'version',
        ]

        self.add_cmd_output(["podman %s" % s for s in subcmds])

        # separately grab ps -s as this can take a *very* long time
        if self.get_option('size'):
            self.add_cmd_output('podman ps -as')

        self.add_journal(units="podman")
        self.add_cmd_output("ls -alhR /etc/cni")

        ps_cmd = 'podman ps -q'
        if self.get_option('all'):
            ps_cmd = "%s -a" % ps_cmd

        img_cmd = 'podman images -q'
        insp = set()

        for icmd in [ps_cmd, img_cmd]:
            result = self.get_command_output(icmd)
            if result['status'] == 0:
                for con in result['output'].splitlines():
                    insp.add(con)

        for container in insp:
            self.add_cmd_output("podman inspect %s" % container)
            if self.get_option('logs'):
                self.add_cmd_output("podman logs -t %s" % container)


# vim: set et ts=4 sw=4 :
