# Copyright (C) 2017 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin


class Rear(Plugin, RedHatPlugin):

    """Relax and Recover
    """

    plugin_name = "rear"
    packages = ('rear',)

    def setup(self):
        limit = self.get_option('log_size')

        # don't collect recovery ISOs or tar archives
        self.add_forbidden_path('/var/log/rear/*.iso')
        self.add_forbidden_path('/var/log/rear/*.tar.gz')

        rdirs = [
            '/etc/rear/*conf',
            '/var/log/rear/*log*'
        ]

        self.add_copy_spec(rdirs, sizelimit=limit)

        self.add_cmd_output([
            'rear -V',
            'rear dump'
        ])

    def postproc(self):
        self.do_path_regex_sub(
            '/etc/rear/*',
            r'SSH_ROOT_PASSWORD=(.*)',
            r'SSH_ROOT_PASSWORD=********'
        )

# vim: set et ts=4 sw=4 :
