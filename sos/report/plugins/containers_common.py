# Copyright (C) 2020 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin, PluginOpt


class ContainersCommon(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Common container configs under {/etc,/usr/share}/containers'
    plugin_name = 'containers_common'
    profiles = ('container', )
    packages = ('containers-common', )
    option_list = [
        PluginOpt('rootlessusers', default='', val_type=str,
                  desc='colon-delimited list of users to collect for')
    ]

    def setup(self):
        self.add_copy_spec([
            '/etc/containers/*',
            '/usr/share/containers/*',
            '/etc/subuid',
            '/etc/subgid',
        ])

        self.add_file_tags({
            "/etc/containers/policy.json": "containers_policy"
        })

        users_opt = self.get_option('rootlessusers')
        users_list = []
        if users_opt:
            users_list = [x for x in users_opt.split(':') if x]

        user_subcmds = [
            'podman info',
            'podman unshare cat /proc/self/uid_map',
            'podman unshare cat /proc/self/gid_map',
            'podman images',
            'podman images --digests',
            'podman pod ps',
            'podman port --all',
            'podman ps',
            'podman ps -a',
            'podman stats --no-stream --all',
            'podman version',
            'podman volume ls',
            'buildah info',
            'buildah unshare cat /proc/self/uid_map',
            'buildah unshare cat /proc/self/gid_map',
            'buildah containers',
            'buildah containers --all',
            'buildah images',
            'buildah images --all',
            'buildah version',
        ]
        for user in users_list:
            # collect user's containers' config
            expanded_user = os.path.expanduser(f'~{user}')
            self.add_copy_spec(
                f'{expanded_user}/.config/containers/')
            # collect user-status
            self.add_cmd_output(f'loginctl user-status {user}')
            # collect the user's related commands
            self.add_cmd_output([
                f'machinectl -q shell {user}@ /usr/bin/{cmd}'
                for cmd in user_subcmds
            ], foreground=True)

# vim: set et ts=4 sw=4 :
