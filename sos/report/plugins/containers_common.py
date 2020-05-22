# Copyright (C) 2020 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import os


class ContainersCommon(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Common container configs under {/etc,/usr/share}/containers'
    plugin_name = 'containers_common'
    profiles = ('container', )
    packages = ('containers-common', )
    option_list = [
        ('rootlessusers', 'colon-separated list of users\' containers info',
         '', ''),
    ]

    def setup(self):
        self.add_copy_spec([
            '/etc/containers/*',
            '/usr/share/containers/*',
            '/etc/subuid',
            '/etc/subgid',
        ])
        self.add_cmd_output(['loginctl user-status'])

        users_opt = self.get_option('rootlessusers')
        users_list = []
        if users_opt:
            users_list = [x for x in users_opt.split(':') if x]

        user_subcmds = [
            'info',
            'unshare cat /proc/self/uid_map',
            'unshare cat /proc/self/gid_map'
        ]
        for user in users_list:
            # collect user's containers' config
            self.add_copy_spec(
                '%s/.config/containers/' % (os.path.expanduser('~%s' % user)))
            # collect the user's podman/buildah info and uid/guid maps
            for binary in ['/usr/bin/podman', '/usr/bin/buildah']:
                for cmd in user_subcmds:
                    self.add_cmd_output([
                        'machinectl -q shell %s@ %s %s' % (user, binary, cmd)
                    ], foreground=True)

# vim: set et ts=4 sw=4 :
