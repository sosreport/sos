# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Anaconda(Plugin, RedHatPlugin):

    short_desc = 'Anaconda installer'

    plugin_name = 'anaconda'
    profiles = ('system',)
    packages = ('anaconda',)

    files = (
        '/var/log/anaconda.log',
        '/var/log/anaconda'
    )

    def setup(self):

        self.copypaths = [
            "/root/anaconda-ks.cfg"
        ]

        if self.path_isdir('/var/log/anaconda'):
            # new anaconda
            self.copypaths.append('/var/log/anaconda')
        else:
            self.copypaths = self.copypaths + [
                "/var/log/anaconda.*",
                "/root/install.log",
                "/root/install.log.syslog"
            ]

        self.add_copy_spec(self.copypaths)

    def postproc(self):
        self.do_file_sub(
            "/root/anaconda-ks.cfg",
            r"(\s*rootpw\s*).*",
            r"\1********"
        )
        self.do_file_sub(
            "/root/anaconda-ks.cfg",
            r"(user.*--password=*\s*)\s*(\S*)",
            r"\1********"
        )
        self.do_paths_http_sub(self.copypaths)

# vim: set et ts=4 sw=4 :
