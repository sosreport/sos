# Copyright (C) 2018 Red Hat, Inc. Daniel Walsh <dwalsh@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CRIO(Plugin):

    """CRI-O containers
    """

    plugin_name = 'crio'
    profiles = ('container',)
    packages = ('cri-o', "cri-tools")

    option_list = [
        ("all", "enable capture for all containers, even containers "
            "that have terminated", 'fast', False),
        ("logs", "capture logs for running containers",
            'fast', False),
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/containers/registries.conf",
            "/etc/containers/storage.conf",
            "/etc/containers/mounts.conf",
            "/etc/containers/policy.json",
            "/etc/crio/crio.conf",
            "/etc/crio/seccomp.json",
            "/etc/systemd/system/cri-o.service",
        ])

        subcmds = [
            'info',
            'images',
            'pods',
            'ps',
            'ps -a',
            'stats',
            'version',
        ]

        self.add_cmd_output(["crictl %s" % s for s in subcmds])
        self.add_journal(units="cri-o")
        self.add_cmd_output("ls -alhR /etc/cni")

        ps_cmd = 'crictl ps --quiet'
        if self.get_option('all'):
            ps_cmd = "%s -a" % ps_cmd

        img_cmd = 'cri-o images --quiet'
        insp = set()

        for icmd in [ps_cmd, img_cmd]:
            result = self.get_command_output(icmd)
            if result['status'] == 0:
                for con in result['output'].splitlines():
                    insp.add(con)

        if insp:
            for container in insp:
                self.add_cmd_output("crictl inspect %s" % container)
                if self.get_option('logs'):
                    self.add_cmd_output("crictl logs -t %s" % container)

# vim: set et ts=4 sw=4 :
