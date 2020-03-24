# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os


class Anaconda(Plugin, RedHatPlugin):
    """Anaconda installer
    """

    plugin_name = 'anaconda'
    profiles = ('system',)
    packages = ('anaconda',)

    files = (
        '/var/log/anaconda.log',
        '/var/log/anaconda'
    )

    def setup(self):

        paths = [
            "/root/anaconda-ks.cfg"
        ]

        if os.path.isdir('/var/log/anaconda'):
            # new anaconda
            paths.append('/var/log/anaconda')
        else:
            paths = paths + [
                "/var/log/anaconda.*",
                "/root/install.log",
                "/root/install.log.syslog"
            ]

        self.add_copy_spec(paths)

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

# vim: set et ts=4 sw=4 :
