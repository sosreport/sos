# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Curtin(Plugin, IndependentPlugin):

    short_desc = 'Curt Installer'

    plugin_name = 'curtin'
    profiles = ('boot',)
    files = ('/root/curtin-install-cfg.yaml', )

    def setup(self):
        self.add_copy_spec([
            '/root/curtin-install.log',
            '/root/curtin-install-cfg.yaml',
            '/etc/default/grub.d/50-curtin-settings.cfg',
            '/etc/apt/apt.conf.d/90curtin-aptproxy',
            '/etc/apt/sources.list.curtin.old',
            '/etc/cloud/cloud.cfg.d/50-curtin-networking.cfg',
            '/etc/cloud/cloud.cfg.d/curtin-preserve-sources.cfg',
        ])

    def postproc(self):
        protect_keys = [
            "oauth_consumer_key",
            "oauth_token_key",
            "token_key",
            "token_secret",
            "consumer_key",
        ]
        curtin_files = [
            "/root/curtin-install-cfg.yaml",
            "/root/curtin-install.log",
        ]

        match_exp_multil = fr"({'|'.join(protect_keys)})\s*(:|=)(\S*\n.*?\\n)"
        match_exp = fr"({'|'.join(protect_keys)})\s*(:|=)\s*[a-zA-Z0-9]*"

        for file in curtin_files:
            self.do_file_sub(
                file, match_exp_multil,
                r"\1\2*********"
            )
            self.do_file_sub(
                file, match_exp,
                r"\1\2*********"
            )

# vim: set et ts=4 sw=4 :
