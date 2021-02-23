# Copyright (C) 2017 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Rear(Plugin, RedHatPlugin):

    short_desc = 'Relax and Recover'
    plugin_name = "rear"
    packages = ('rear',)

    def setup(self):
        # don't collect recovery ISOs or tar archives
        self.add_forbidden_path([
            '/var/lib/rear/output/*'
        ])

        self.add_copy_spec([
            '/etc/rear/*conf',
            '/etc/rear/mappings/*',
            '/var/lib/rear/layout/*',
            '/var/lib/rear/recovery/*',
            '/var/log/rear/*log*'
        ])

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
