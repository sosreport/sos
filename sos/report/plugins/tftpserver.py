# Copyright (C) 2007 Shijoe George <spanjikk@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class TftpServer(Plugin, IndependentPlugin):

    short_desc = 'TFTP Server information'
    plugin_name = 'tftpserver'
    profiles = ('sysmgmt', 'network')
    services = ('tftp', 'tftpd-hpa')
    files = ('/etc/xinetd.d/tftp',)
    packages = ('tftp-server', 'tftpd-hpa')
    option_list = [
        PluginOpt('tftpboot', default=False,
                  desc='collect content from tftpboot path')
    ]

    def setup(self):
        self.add_copy_spec('/etc/default/tftp-hpa')

        tftp_dirs = [
            '/srv/tftp',
            '/tftpboot',
            '/var/lib/tftpboot',
        ]
        self.add_dir_listing(tftp_dirs, recursive=True)

        if self.get_option('tftpboot'):
            self.add_copy_spec(tftp_dirs)

# vim: set et ts=4 sw=4 :
