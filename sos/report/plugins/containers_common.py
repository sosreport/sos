# Copyright (C) 2020 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin, PluginOpt
import os


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
            self.add_copy_spec(
                '%s/.config/containers/' % (os.path.expanduser('~%s' % user)))
            # collect user-status
            self.add_cmd_output('loginctl user-status %s' % user)
            # collect the user's related commands
            self.add_cmd_output([
                'machinectl -q shell %s@ /usr/bin/%s' % (user, cmd)
                for cmd in user_subcmds
            ], foreground=True)

# vim: set et ts=4 sw=4 :
